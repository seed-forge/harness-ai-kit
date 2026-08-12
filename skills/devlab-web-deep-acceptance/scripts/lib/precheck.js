/**
 * lib/precheck.js — 开测前后端 SQL 链路预检（通用化版）。
 *
 * 背景：后端 DB 访问代理吞 SQL 异常（表缺/列缺/函数缺/方言）统一返回 200+空/null，
 * 接口层无法区分"合法空"与"假成功"；不预检会导致"数据空需造数"误判与多轮追根因。
 *
 * 用法：node run.js <module> --precheck
 * 前置：registry/<module>.yaml 顶层 backend_mappers（mapper/SQL 目录列表）。
 * DB 通道：e2e.config.js dbServerUrl（只读 HTTP 代理，POST {sql}）。
 *   留空时 DB 段自动降级为"仅静态方言扫描"并在报告注明。
 *   通道特性注意：某些代理 SQL 报错返回空体而非错误结构（空体≠零行）。
 *
 * 四段检查（1 为纯静态不依赖 DB；2-4 依赖 DB 通道）：
 *   1) 方言静态扫描：目标 DB 不支持的形态（默认规则为 PG→Oracle，可按项目改 DIALECT_RULES），
 *      高置信计入退出码，观察级仅列报告。
 *   2) 表存在性批扫。
 *   3) 自定义函数存在性（f_/fn_ 前缀引用 ↔ FUNCTION/PROCEDURE/PACKAGE）。
 *   4) 列存在性（alias.col ↔ all_tab_columns；仅对"别名→物理表映射无歧义"的引用判缺，宁漏勿误报）。
 *
 * 输出（stdout + reports/<module>/PRECHECK.md）；退出码（run.js）：
 *   0=全部通过；3=有缺失表/函数/列或高置信方言；2=预检自身故障（含 DB 通道不可用）。
 */
const fs = require('fs');
const path = require('path');
const http = require('http');

// SQL 关键字与函数名——正则抽表名的误报剔除表（保守收录，宁可多报表名让 DB 批扫甄别）
const NOT_TABLES = new Set([
  'SELECT', 'DUAL', 'WHERE', 'AND', 'OR', 'ON', 'SET', 'VALUES', 'TABLE',
  'LATERAL', 'UNNEST', 'GENERATE_SERIES', 'INTERVAL', 'CASE', 'WHEN',
  'LEFT', 'RIGHT', 'INNER', 'OUTER', 'FULL', 'CROSS', 'GROUP', 'ORDER', 'BY',
  'UNION', 'ALL', 'DISTINCT', 'NOT', 'EXISTS',
]);

// 别名判定的关键字剔除（from t WHERE… 的 WHERE 不是别名）
const NOT_ALIAS = new Set([
  ...NOT_TABLES, 'JOIN', 'USING', 'START', 'CONNECT', 'HAVING', 'FOR', 'MINUS',
  'INTERSECT', 'FETCH', 'LIMIT', 'OFFSET', 'PARTITION', 'MODEL', 'PIVOT', 'UNPIVOT', 'AS', 'A',
]);

// 列引用剔除：伪列/dual 场景/动态片段常见左标识符
const NOT_COLUMNS = new Set(['ROWNUM', 'ROWID', 'LEVEL', 'NEXTVAL', 'CURRVAL', 'SYSDATE']);

/**
 * 把 XML 文本转成"等长 SQL 文本"：注释/CDATA 包装/标签替换为等长空白（保留换行），
 * 使后续 matchAll 的 index 能换算准确行号（静扫需要 file:line 定位）。
 */
function toSqlTextKeepLines(xmlText) {
  const blank = m => m.replace(/[^\n]/g, ' ');
  return xmlText
    .replace(/<!--[\s\S]*?-->/g, blank)
    .replace(/<!\[CDATA\[|\]\]>/g, blank)
    .replace(/<\/?[a-zA-Z!][^>]*>/g, blank);
}

function lineOf(text, index) {
  let n = 1;
  for (let i = 0; i < index && i < text.length; i++) if (text[i] === '\n') n++;
  return n;
}

/** 从单个 mapper XML 文本抽物理表名（FROM/JOIN/INTO/UPDATE/DELETE FROM 后的标识符） */
function extractTables(xmlText) {
  const tables = new Set();
  const sql = toSqlTextKeepLines(xmlText);
  // CTE 名排除：WITH tp AS / , tp2 AS / 带列清单 WITH tp (a,b) AS / PG 递归 WITH RECURSIVE tp AS
  const cteNames = new Set();
  for (const m of sql.matchAll(/(?:\bwith(?:\s+recursive)?|,)\s+([a-zA-Z][\w$#]*)\s*(?:\([^)]*\))?\s+as\s*\(/gi)) cteNames.add(m[1].toUpperCase());
  const re = /\b(?:from|join|insert\s+into|update|delete\s+from|merge\s+into)\s+([a-zA-Z][\w$#]*(?:\.[a-zA-Z][\w$#]*)?)/gi;
  let m;
  while ((m = re.exec(sql)) !== null) {
    let name = m[1].toUpperCase();
    if (name.includes('.')) name = name.split('.').pop();
    if (NOT_TABLES.has(name) || cteNames.has(name)) continue;
    tables.add(name);
  }
  return tables;
}

// ==================== 1) 方言静态扫描（纯静态） ====================
// level: 'high' 计入退出码（目标 DB 必炸/必被吞）；'warn' 只列报告（需人工甄别）
// 默认规则集 = PG→Oracle 迁移形态；其他 DB 组合按项目增删。
const DIALECT_RULES = [
  {
    id: 'partition-no-orderby', level: 'high',
    label: 'over(partition by) 缺 order by → ORA-30485，整条 SQL 被吞成 200+空',
    // 单独实现（需检查括号组内部），见 findNakedPartitionBy
  },
  { id: 'pg-cast', level: 'high', label: '`::` 类型转换（PG-only）', re: /::\s*[a-zA-Z]+/g },
  { id: 'limit', level: 'high', label: 'LIMIT 行限制（Oracle 需 FETCH FIRST/ROWNUM）', re: /\blimit\s+\d+/gi },
  { id: 'ilike', level: 'high', label: 'ILIKE（PG-only）', re: /\bilike\b/gi },
  { id: 'now-fn', level: 'high', label: 'now()（Oracle 无此函数）', re: /\bnow\s*\(\s*\)/gi },
  { id: 'on-conflict', level: 'high', label: 'ON CONFLICT upsert（PG-only）', re: /\bon\s+conflict\b/gi },
  { id: 'string-agg', level: 'high', label: 'string_agg()（Oracle 用 LISTAGG）', re: /\bstring_agg\s*\(/gi },
  { id: 'split-part', level: 'high', label: 'split_part()（PG-only）', re: /\bsplit_part\s*\(/gi },
  { id: 'interval-str-arith', level: 'warn', label: "日期 ± 'N days' 字符串运算（PG 形态）", re: /[+-]\s*'\s*\d+\s*(?:day|days|month|months|hour|hours|minute|minutes)\s*'/gi },
  { id: 'substring-from', level: 'warn', label: 'substring(x from y)（PG 形态，Oracle 用 substr）', re: /\bsubstring\s*\([^)]*\bfrom\b/gi },
  { id: 'date-trunc', level: 'warn', label: 'date_trunc()（PG 形态）', re: /\bdate_trunc\s*\(/gi },
];

/** 裸 partition by 检测：over( partition by ... ) 括号组内无 order by（含尾空格变体） */
function findNakedPartitionBy(sql) {
  const out = [];
  const re = /\bover\s*\(\s*partition\s+by\b/gi;
  let m;
  while ((m = re.exec(sql)) !== null) {
    const open = sql.indexOf('(', m.index);
    let depth = 0, end = -1;
    for (let i = open; i < sql.length && i < open + 2000; i++) {
      if (sql[i] === '(') depth++;
      else if (sql[i] === ')') { depth--; if (depth === 0) { end = i; break; } }
    }
    const body = end > 0 ? sql.slice(open, end) : sql.slice(open, open + 200);
    if (!/\border\s+by\b/i.test(body)) out.push({ index: m.index, snippet: sql.slice(m.index, Math.min(end > 0 ? end + 1 : m.index + 80, m.index + 120)).replace(/\s+/g, ' ') });
  }
  return out;
}

/** 对单文件跑全部方言规则，返回 [{ruleId,level,label,line,snippet}] */
function scanDialect(xmlText) {
  const sql = toSqlTextKeepLines(xmlText);
  const findings = [];
  for (const hit of findNakedPartitionBy(sql)) {
    findings.push({ ruleId: 'partition-no-orderby', level: 'high', label: DIALECT_RULES[0].label, line: lineOf(sql, hit.index), snippet: hit.snippet.slice(0, 100) });
  }
  for (const rule of DIALECT_RULES) {
    if (!rule.re) continue;
    rule.re.lastIndex = 0;
    let m;
    while ((m = rule.re.exec(sql)) !== null) {
      findings.push({ ruleId: rule.id, level: rule.level, label: rule.label, line: lineOf(sql, m.index), snippet: sql.slice(m.index, m.index + 60).replace(/\s+/g, ' ') });
    }
  }
  return findings;
}

// ==================== 3) 自定义函数引用抽取 ====================
/** f_/fn_ 前缀调用形抽取（项目自定义函数命名约定，按项目调整正则） */
function extractFunctions(xmlText) {
  const sql = toSqlTextKeepLines(xmlText);
  const out = new Set();
  for (const m of sql.matchAll(/\b(f(?:n)?_[a-zA-Z0-9_$#]+)\s*\(/gi)) out.add(m[1].toUpperCase());
  return out;
}

// ==================== 4) 列引用抽取（保守版：仅无歧义别名） ====================
/**
 * 返回 { aliasMap: Map<alias, Set<table>>, colRefs: Map<alias, Set<col>> }。
 * 只认 `from|join <物理表> <别名>` 直连别名（子查询别名 `) x` 不会命中，天然排除）；
 * 动态片段 #{}/${} 内不抽。调用方仅对"别名→恰好一张已存在物理表"的组合判列缺失。
 */
function extractColumnRefs(xmlText) {
  const sql = toSqlTextKeepLines(xmlText).replace(/[#$]\{[^}]*\}/g, ' ');
  const aliasMap = new Map();
  const re = /\b(?:from|join|update)\s+([a-zA-Z][\w$#]*)\s+(?:as\s+)?([a-zA-Z][\w$#]*)\b/gi;
  let m;
  while ((m = re.exec(sql)) !== null) {
    const table = m[1].toUpperCase();
    const alias = m[2].toUpperCase();
    if (NOT_TABLES.has(table) || NOT_ALIAS.has(alias)) continue;
    if (!aliasMap.has(alias)) aliasMap.set(alias, new Set());
    aliasMap.get(alias).add(table);
  }
  const colRefs = new Map();
  for (const c of sql.matchAll(/\b([a-zA-Z][\w$#]*)\.([a-zA-Z][\w$#]*)\b/g)) {
    const alias = c[1].toUpperCase();
    const col = c[2].toUpperCase();
    if (!aliasMap.has(alias) || NOT_COLUMNS.has(col)) continue;
    if (!colRefs.has(alias)) colRefs.set(alias, new Set());
    colRefs.get(alias).add(col);
  }
  return { aliasMap, colRefs };
}

/** 递归收集目录下 mapper xml / sql 文件 */
function listMapperFiles(dir) {
  const out = [];
  if (!fs.existsSync(dir)) return out;
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) out.push(...listMapperFiles(p));
    else if (e.isFile() && /\.(xml|sql)$/i.test(e.name)) out.push(p);
  }
  return out;
}

/** DB 通道直查（超时/非200/空体均显式区分）。dbServerUrl 形如 http://host:port/oracle */
function dbQuery(dbServerUrl, sql, timeoutMs = 20000) {
  return new Promise((resolve, reject) => {
    const payload = JSON.stringify({ sql });
    const u = new URL('/queryForList', dbServerUrl.endsWith('/') ? dbServerUrl : dbServerUrl + '/');
    const req = http.request(u, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json;charset=utf-8', 'Content-Length': Buffer.byteLength(payload) },
      timeout: timeoutMs,
    }, res => {
      let data = '';
      res.on('data', ch => { data += ch; });
      res.on('end', () => {
        if (res.statusCode !== 200) return reject(new Error(`dbserver HTTP ${res.statusCode}: ${data.slice(0, 120)}`));
        if (!data.trim()) return reject(new Error('dbserver 返回空体（该通道空体=SQL 报错，非零行）'));
        try { resolve(JSON.parse(data)); }
        catch (e) { reject(new Error(`dbserver 响应非 JSON: ${data.slice(0, 120)}`)); }
      });
    });
    req.on('timeout', () => { req.destroy(new Error(`dbserver 请求超时(${timeoutMs}ms)`)); });
    req.on('error', reject);
    req.write(payload);
    req.end();
  });
}

/** 取一列字段值（大小写/驼峰容错） */
function colVal(row, name) {
  return row[name] || row[name.toLowerCase()] || row[name.toLowerCase().replace(/_([a-z])/g, (s, c) => c.toUpperCase())];
}

/** 分批查 all_objects 指定类型，返回存在的对象名 Set（Oracle 字典视图；其他 DB 改 information_schema） */
async function queryExistingObjects(dbUrl, names, types) {
  const existing = new Set();
  const arr = [...names];
  const typeList = types.map(t => `'${t}'`).join(',');
  for (let i = 0; i < arr.length; i += 200) {
    const inList = arr.slice(i, i + 200).map(t => `'${t.replace(/'/g, '')}'`).join(',');
    const rows = await dbQuery(dbUrl, `select object_name from all_objects where object_type in (${typeList}) and object_name in (${inList})`);
    for (const r of rows || []) {
      const v = colVal(r, 'OBJECT_NAME');
      if (v) existing.add(String(v).toUpperCase());
    }
  }
  return existing;
}

async function queryExisting(dbUrl, tableNames) {
  return queryExistingObjects(dbUrl, tableNames, ['TABLE', 'VIEW', 'SYNONYM', 'MATERIALIZED VIEW']);
}

/** 分批查 all_tab_columns，返回 Map<table, Set<column>> */
async function queryColumns(dbUrl, tableNames) {
  const out = new Map();
  const arr = [...tableNames];
  for (let i = 0; i < arr.length; i += 100) {
    const inList = arr.slice(i, i + 100).map(t => `'${t.replace(/'/g, '')}'`).join(',');
    const rows = await dbQuery(dbUrl, `select table_name, column_name from all_tab_columns where table_name in (${inList})`);
    for (const r of rows || []) {
      const t = String(colVal(r, 'TABLE_NAME') || '').toUpperCase();
      const c = String(colVal(r, 'COLUMN_NAME') || '').toUpperCase();
      if (!t || !c) continue;
      if (!out.has(t)) out.set(t, new Set());
      out.get(t).add(c);
    }
  }
  return out;
}

/**
 * 主入口。返回 { ok, missing, present, tableRefs, dialect, missingFuncs, missingCols,
 * dbSkipped, reportFile }；配置类故障抛 Error（exit 2）；DB 通道故障不抛——降级为
 * "仅静态段"落盘报告并置 dbSkipped=错误信息（run.js 据此 exit 2 但静态结论可用）。
 */
async function precheck(moduleId, registry, baseDir, config = {}) {
  const dbUrl = config.dbServerUrl || '';
  const mapperDirs = registry.backend_mappers;
  if (!Array.isArray(mapperDirs) || !mapperDirs.length) {
    throw new Error(
      `registry/${moduleId}.yaml 未配置顶层 backend_mappers（mapper/SQL 目录列表）。示例：\n`
      + `backend_mappers:\n  - ../../<repo>/<service>/src/main/resources/mapper`);
  }
  // -------- 静态段：抽表/函数/列引用 + 方言扫描 --------
  const tableRefs = new Map();
  const funcRefs = new Map();
  const dialect = [];
  const fileCols = [];
  let fileCount = 0;
  for (const d of mapperDirs) {
    const abs = path.isAbsolute(d) ? d : path.resolve(baseDir, d);
    const files = listMapperFiles(abs);
    if (!files.length) console.warn(`[precheck] 警告：目录无 mapper/sql 文件或不存在：${abs}`);
    for (const f of files) {
      fileCount++;
      const text = fs.readFileSync(f, 'utf-8');
      const base = path.basename(f);
      for (const t of extractTables(text)) {
        if (!tableRefs.has(t)) tableRefs.set(t, new Set());
        tableRefs.get(t).add(base);
      }
      for (const fn of extractFunctions(text)) {
        if (!funcRefs.has(fn)) funcRefs.set(fn, new Set());
        funcRefs.get(fn).add(base);
      }
      for (const hit of scanDialect(text)) dialect.push({ file: base, ...hit });
      fileCols.push({ file: base, ...extractColumnRefs(text) });
    }
  }
  if (!tableRefs.size) throw new Error(`从 ${fileCount} 个文件抽取到 0 张表——检查 backend_mappers 路径`);
  const dialectHigh = dialect.filter(x => x.level === 'high');

  // -------- DB 段：表/函数/列存在性（DB 不可用/未配置 → 降级仅静态） --------
  let dbSkipped = null;
  let missing = [], present = [], missingFuncs = [], missingCols = [];
  if (!dbUrl) {
    dbSkipped = 'dbServerUrl 未配置（e2e.config.js）';
  } else {
    try {
      const existing = await queryExisting(dbUrl, new Set(tableRefs.keys()));
      missing = [...tableRefs.keys()].filter(t => !existing.has(t)).sort();
      present = [...tableRefs.keys()].filter(t => existing.has(t)).sort();

      if (funcRefs.size) {
        const fnExisting = await queryExistingObjects(dbUrl, new Set(funcRefs.keys()), ['FUNCTION', 'PROCEDURE', 'PACKAGE']);
        missingFuncs = [...funcRefs.keys()].filter(f => !fnExisting.has(f)).sort();
      }
      // 列级：仅对存在的物理表 + 无歧义别名判缺（宁漏勿误报）
      const colsByTable = await queryColumns(dbUrl, present);
      const colMissSet = new Set();
      for (const { file, aliasMap, colRefs } of fileCols) {
        for (const [alias, cols] of colRefs) {
          const tables = aliasMap.get(alias);
          if (!tables || tables.size !== 1) continue; // 别名歧义/映射到子查询 → 跳过
          const table = [...tables][0];
          const tCols = colsByTable.get(table);
          if (!tCols) continue; // 表不存在/未取到列 → 已由表级覆盖
          for (const col of cols) {
            if (!tCols.has(col)) colMissSet.add(JSON.stringify({ table, col, file }));
          }
        }
      }
      missingCols = [...colMissSet].map(s => JSON.parse(s)).sort((a, b) => (a.table + a.col).localeCompare(b.table + b.col));
    } catch (e) {
      dbSkipped = e.message;
    }
  }

  const ok = !dbSkipped && !missing.length && !missingFuncs.length && !missingCols.length && !dialectHigh.length;

  // -------- 报告落盘 --------
  const lines = [];
  lines.push(`# ${moduleId} — 开测前后端 SQL 链路预检（PRECHECK v2）`);
  lines.push(`- 时间: ${new Date().toISOString().slice(0, 10)}  | mapper 文件: ${fileCount}  | 抽取表: ${tableRefs.size}  | 函数引用: ${funcRefs.size}`);
  if (dbSkipped) {
    lines.push(`- ⚠ DB 通道不可用（${dbSkipped}）——表/列/函数存在性未检，本报告仅含静态方言段，恢复后重跑`);
  }
  lines.push(`- 结论: ${ok ? '✅ 全部通过' : `⚠ ${[
    missing.length && `缺表${missing.length}`,
    missingFuncs.length && `缺函数${missingFuncs.length}`,
    missingCols.length && `缺列${missingCols.length}`,
    dialectHigh.length && `高置信方言${dialectHigh.length}处`,
    dbSkipped && 'DB段未检',
  ].filter(Boolean).join(' / ')}——命中查询将呈"200+空/null 假成功"或 500，预判 blocked`}`);
  lines.push('');
  if (dialect.length) {
    lines.push('## 方言静态扫描（high 计入退出码，warn 供人工甄别）');
    lines.push('| 级别 | 形态 | 位置 | 片段 |');
    lines.push('|------|------|------|------|');
    for (const d of dialect) lines.push(`| ${d.level} | ${d.ruleId} | ${d.file}:${d.line} | \`${d.snippet.replace(/\|/g, '\\|')}\` |`);
    lines.push('');
  }
  if (missing.length) {
    lines.push('## 缺失表（预判 blocked，登记 pending-issues 引用本报告）');
    lines.push('| 表名 | 引用文件 |');
    lines.push('|------|----------|');
    for (const t of missing) lines.push(`| ${t} | ${[...tableRefs.get(t)].join(', ')} |`);
    lines.push('');
  }
  if (missingFuncs.length) {
    lines.push('## 缺失函数/过程（命中 SQL 整条被吞）');
    lines.push('| 函数 | 引用文件 |');
    lines.push('|------|----------|');
    for (const f of missingFuncs) lines.push(`| ${f} | ${[...funcRefs.get(f)].join(', ')} |`);
    lines.push('');
  }
  if (missingCols.length) {
    lines.push('## 缺失列（保守判定：仅无歧义别名直连物理表；命中 SQL 整条被吞）');
    lines.push('| 表.列 | 引用文件 |');
    lines.push('|-------|----------|');
    for (const c of missingCols) lines.push(`| ${c.table}.${c.col} | ${c.file} |`);
    lines.push('');
  }
  lines.push(`## 存在表（${present.length}）${dbSkipped ? '（DB 未检）' : ''}`);
  lines.push(present.join(', ') || '（无/未检）');
  const reportDir = path.join(baseDir, 'reports', moduleId);
  fs.mkdirSync(reportDir, { recursive: true });
  const reportFile = path.join(reportDir, 'PRECHECK.md');
  fs.writeFileSync(reportFile, lines.join('\n') + '\n', 'utf-8');

  return { ok, missing, present, tableRefs, dialect, dialectHigh, missingFuncs, missingCols, funcRefs, dbSkipped, reportFile };
}

module.exports = {
  precheck, extractTables, extractFunctions, extractColumnRefs,
  scanDialect, findNakedPartitionBy, toSqlTextKeepLines, dbQuery,
};
