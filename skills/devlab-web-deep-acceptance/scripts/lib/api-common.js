/**
 * lib/api-common.js — 跨模块公共原语（通用化版）。
 * 项目专属组件原语（如某组件库的树选择/表单读取）不进本文件——放项目侧 cases/<module>/_helpers.js。
 * 本文件只收与组件库无关的通用机制：响应体分诊、API 捕获、白屏自愈、DB 通道。
 */
const path = require('path');
const config = require(path.join(__dirname, '..', 'e2e.config.js'));

// ==================== 响应体六态分诊 ====================

/**
 * 响应体六态分诊：HTTP 200 ≠ 业务成功（吞错家族同构）。
 * 入参为 captureApis 单项 { hits, status, body }；
 * 返回 no-hit | http:N | code:500 | result:null | empty | data。
 * 断言/探针一律先分诊再定 pass-empty/blocked。
 */
function bodyVerdict(a) {
  if (!a || !a.hits) return 'no-hit';
  if (a.status != null && a.status >= 400) return `http:${a.status}`;
  const b = a.body || {};
  const bizOk = String(config.bizSuccessCode || '200');
  if (b.code != null && String(b.code) !== bizOk) return `code:${b.code}`;
  if (!('result' in b) || b.result == null) return 'result:null';
  if (Array.isArray(b.result) && b.result.length === 0) return 'empty';
  if (typeof b.result === 'object' && Object.keys(b.result).length === 0) return 'empty';
  return 'data';
}

/** 假成功判定：code:非成功/result:null 属吞错态（非合法空） */
function isSwallowedError(v) { return /^code:/.test(v) || v === 'result:null'; }

/** 批量分诊摘要："key1=data key2=code:500 ..."（写入报告 detail） */
function verdictSummary(apis) { return apis.map(a => `${a.key}=${bodyVerdict(a)}`).join(' '); }

// ==================== API 响应捕获 ====================

/**
 * 捕获匹配 pattern 的响应，collect() 汇总每项 { key, status, body, hits }。
 * - collect(retryWaitMs=5000)：汇总已到达响应；若有 ≥400 再等一次重获（间歇抖动兜底）。
 * - .hits(key)：该 key 命中次数。
 * - .waitForHit(key, timeoutMs=8000)：轮询等目标请求到达再 collect——自动查询页
 *   (mounted 即发查询) 查询异步发起，gotoPage/reload 可能先返回致 collect() 立即拿
 *   status:null 误判"接口未发起"FAIL。
 */
function captureApis(page, specs) {
  const results = specs.map(s => ({ key: s.key, status: null, body: null, hits: 0 }));
  const pending = [];
  const handler = r => {
    specs.forEach((s, i) => {
      if (!s.pattern.test(r.url())) return;
      results[i].hits++;
      pending.push(
        r.json().then(b => ({ i, status: r.status(), body: b }))
          .catch(() => ({ i, status: r.status(), body: null }))
      );
    });
  };
  page.on('response', handler);
  const apply = settled => settled.forEach(s => { results[s.i].status = s.status; results[s.i].body = s.body; });
  const collectFn = async (retryWaitMs = 5000) => {
    apply(await Promise.all(pending));
    if (results.some(x => x.status !== null && x.status >= 400)) {
      await page.waitForTimeout(retryWaitMs);
      apply(await Promise.all(pending));
    }
    page.off('response', handler);
    return results;
  };
  collectFn.hits = key => { const r = results.find(x => x.key === key); return r ? r.hits : 0; };
  collectFn.waitForHit = async (key, timeoutMs = 8000) => {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      if (collectFn.hits(key) > 0) return true;
      await page.waitForTimeout(200);
    }
    return false;
  };
  return collectFn;
}

// ==================== 导航与就绪 ====================

/** 白屏甄别：主内容区存在且有可见文本 */
async function pageHasContent(page, minTextLen = 20, rootSelector = null) {
  return page.evaluate(({ min, rootSel }) => {
    const root = (rootSel && document.querySelector(rootSel)) || document.querySelector('#app') || document.body;
    return !!root && (root.innerText || '').trim().length >= min;
  }, { min: minTextLen, rootSel: rootSelector });
}

/** 等待业务组件挂载（微前端门户重启耗时不定，不用固定 sleep） */
async function waitBusinessReady(page, { componentSelector = null, rootSelector = null } = {}) {
  await page.waitForFunction(({ compSel, rootSel }) => {
    if (compSel && document.querySelector(compSel)) return true;
    const root = (rootSel && document.querySelector(rootSel)) || document.querySelector('#app');
    return !!root && (root.innerText || '').trim().length >= 50;
  }, { compSel: componentSelector, rootSel: rootSelector }, { timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(3000);
}

/**
 * 进入目标页（白屏自愈）：hash 切换 → 整页 reload 保证全新挂载 →
 * 若主内容区仍空（微前端门户偶发挂载失败）再 reload 一次。
 * 微前端 SPA hash 导航遗留脏状态（keep-alive 页签不随路由变、组件复用致 mounted 不触发），
 * 跨用例必须真 reload。
 */
async function gotoPageResilient(page, session, route, opts = {}) {
  const pathPart = route.replace(/^#/, '');
  if (!page.url().includes(pathPart)) {
    await page.evaluate(h => { location.hash = h; }, pathPart);
    await page.waitForTimeout(500);
  }
  await page.reload({ waitUntil: 'networkidle', timeout: 45000 }).catch(() => {});
  await waitBusinessReady(page, opts);
  if (!(await pageHasContent(page, 20, opts.rootSelector))) {
    await page.reload({ waitUntil: 'networkidle', timeout: 45000 }).catch(() => {});
    await waitBusinessReady(page, opts);
  }
}

// ==================== DB 直查/造数通道（可选，需 config.dbServerUrl） ====================
// 写接口（insert/update/delete）空闲后首发常 502 间歇抖动，必须重试；读接口偶发同样抖动。
// fail-fast 探活：db 通道首次使用时 select 1 from dual 验通，死通道立即抛明确错误而非静默假成功。
const DBSERVER = config.dbServerUrl || '';

let _dbAlive = false;
async function ensureDbAlive({ tries = 3, gapMs = 1000 } = {}) {
  if (_dbAlive) return;
  if (!DBSERVER) throw new Error('dbServerUrl 未配置（e2e.config.js）——DB 通道不可用');
  let last;
  for (let i = 0; i < tries; i++) {
    try {
      const res = await fetch(`${DBSERVER}/queryForList`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ sql: 'select 1 from dual' }),
      });
      if (res.status === 200) { _dbAlive = true; return; }
      last = `http ${res.status}`;
    } catch (e) { last = e.message; }
    await new Promise(r => setTimeout(r, gapMs));
  }
  throw new Error(`dbserver 通道不可用（${DBSERVER}）: ${last}——检查网络可达性，或 export E2E_DBSERVER 覆盖端点`);
}

/** dbserver 查询（带 502 重试 + 首次使用探活）。返回解析后的数组/对象；连续失败抛错。 */
async function dbQuery(sql, { tries = 5, gapMs = 1500 } = {}) {
  await ensureDbAlive();
  let last;
  for (let i = 0; i < tries; i++) {
    try {
      const res = await fetch(`${DBSERVER}/queryForList`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ sql }),
      });
      if (res.status === 200) { const t = await res.text(); return t ? JSON.parse(t) : []; }
      last = `http ${res.status}`;
    } catch (e) { last = e.message; }
    await new Promise(r => setTimeout(r, gapMs));
  }
  throw new Error(`dbQuery 连续 ${tries} 次失败: ${last}`);
}

/**
 * dbserver 写操作（insert/update/delete，带 502 重试）。返回影响行数（int）。
 * ⚠ 配套铁律（务必遵守，否则静默丢数据）：
 *  - 多列长 INSERT / 多 SET 长 UPDATE 可能被 SQL 翻译器静默吃掉（返 200 但 0 行）→
 *    宽表先窄插（仅 NOT NULL 列），其余列逐列单 SET UPDATE 补齐；
 *  - `from dual` 与 `(select 1) tmp` 在部分代理均不可用，insert...select 幂等写法借真实表：
 *    `select … from <字典表> where rownum=1 and not exists(…)`；
 *  - 返回行数不可信，落库成败一律用 dbQuery 复核。
 * @param endpoint 'insert' | 'update' | 'delete'
 */
async function dbWrite(endpoint, sql, { tries = 6, gapMs = 1500 } = {}) {
  await ensureDbAlive();
  let last;
  for (let i = 0; i < tries; i++) {
    try {
      const res = await fetch(`${DBSERVER}/${endpoint}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ sql }),
      });
      if (res.status === 200) return Number((await res.text()).trim()) || 0;
      last = `http ${res.status}`;
    } catch (e) { last = e.message; }
    await new Promise(r => setTimeout(r, gapMs));
  }
  throw new Error(`dbWrite(${endpoint}) 连续 ${tries} 次失败: ${last}`);
}

module.exports = {
  bodyVerdict, isSwallowedError, verdictSummary,
  captureApis,
  pageHasContent, waitBusinessReady, gotoPageResilient,
  DBSERVER, ensureDbAlive, dbQuery, dbWrite,
};
