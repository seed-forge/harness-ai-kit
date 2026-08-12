#!/usr/bin/env node
/**
 * run.js — 深度验收唯一入口（通用化版）。用法：
 *   node run.js <module> --dry-run   # 登录+导航+列出功能点（不执行用例）
 *   node run.js <module>             # 默认执行 fail/blocked/todo（跳过 pass）
 *   node run.js <module> --all       # 全量回归（自动跳过 blocked + 带 reason 的终态 fail）
 *   node run.js <module> --all --rerun-fail  # 连带强制重跑终态 fail
 *   node run.js <module> --case <id> # 单点
 *   node run.js <module> --seed      # 造数（调 data/factory/<module>.js）
 *   node run.js <module> --cleanup   # 清理造数
 *   node run.js <module> --precheck  # 开测前 SQL 链路预检（表/列/函数三级+方言静扫，需 registry 配 backend_mappers）
 *   node run.js <module> --audit     # 收尾三对齐审计：status × 用例文件 × 报告（不拉浏览器）
 *   node run.js <module> --retry N   # 案例级重试上限（默认 2，仅对 fail 重跑）
 *   node run.js <module> --headed    # 有头调试
 *
 * 环境差异全部走 e2e.config.js（从 e2e.config.example.js 拷贝）。新增模块零改本文件。
 *
 * registry 回写铁律（血泪教训固化）：
 * - 文本级精准替换（不用 yaml.dump 重写——会丢失 # 执行注等全部注释，注释是经验载体）；
 * - 写回前用 js-yaml 回验解析，失败则放弃落盘并告警（YAML 炸会废掉整个 registry）；
 * - reason 用单引号 YAML 标量，内部单引号翻倍转义；换行压平——JS 错误栈多行文案注入
 *   会炸 "multiline key"；截断 300 字符；
 * - 回写失败标记 → 收尾非零退出码 3。
 */
const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');

const E2E = __dirname;
const config = require(path.join(E2E, 'e2e.config.js'));
const browserLib = require('./lib/browser');
const session = require('./lib/session');
const assert = require('./lib/assert');
const actions = require('./lib/actions');
const report = require('./lib/report');

const argv = process.argv.slice(2);
const moduleId = argv[0] && !argv[0].startsWith('--') ? argv[0] : null;
const flags = new Set(argv.filter(a => a.startsWith('--')));
const caseId = (() => { const i = argv.indexOf('--case'); return i >= 0 ? argv[i + 1] : null; })();

function loadRegistry(id) {
  const file = path.join(E2E, 'registry', `${id}.yaml`);
  return yaml.load(fs.readFileSync(file, 'utf-8'));
}

let __registryWriteOk = true; // 回写失败标记 → 收尾非零退出码 3

/** 文本级回写 registry：就地替换 status/last_run/reason，保全部注释 */
function writeBackRegistry(id, resultsToWrite) {
  const file = path.join(E2E, 'registry', `${id}.yaml`);
  const lines = fs.readFileSync(file, 'utf-8').split('\n');
  const today = new Date().toISOString();
  for (const r of resultsToWrite) {
    // 定位 feature 块："- id: <featureId>" 行 → 其后的 status: 行
    const idIdx = lines.findIndex(l => new RegExp(`^\\s*-\\s+id:\\s+${r.featureId}\\s*$`).test(l));
    if (idIdx < 0) { console.warn(`[registry] ⚠ 未找到 feature ${r.featureId}，跳过回写`); continue; }
    const findIdx = (re) => {
      for (let i = idIdx + 1; i < lines.length; i++) {
        if (/^\s*-\s+id:/.test(lines[i])) return -1; // 越界到下一个 feature
        if (re.test(lines[i])) return i;
      }
      return -1;
    };
    const statusIdx = findIdx(/^\s*status:/);
    if (statusIdx < 0) continue;
    const indent = lines[statusIdx].match(/^\s*/)[0];
    lines[statusIdx] = `${indent}status: ${r.status}`;
    const wantReason = (r.status === 'blocked' || r.status === 'fail') && r.reason;
    const reasonLine = wantReason
      ? `${indent}reason: '${String(r.reason).replace(/\s*\n\s*/g, ' ').slice(0, 300).replace(/'/g, "''")}'`
      : null;
    // 1) last_run 就地替换或插入 status 之后
    const lastRunIdx = findIdx(/^\s*last_run:/);
    if (lastRunIdx >= 0) lines[lastRunIdx] = `${indent}last_run: ${today}`;
    else lines.splice(statusIdx + 1, 0, `${indent}last_run: ${today}`);
    // 2) reason 就地替换/删除/插入（重扫定位，规避上一步 splice 位移）
    const reasonIdx = findIdx(/^\s*reason:/);
    if (reasonIdx >= 0) {
      if (reasonLine) lines[reasonIdx] = reasonLine;
      else lines.splice(reasonIdx, 1);
    } else if (reasonLine) {
      lines.splice(findIdx(/^\s*last_run:/) + 1, 0, reasonLine);
    }
  }
  const text = lines.join('\n');
  try {
    yaml.load(text); // 回验
  } catch (e) {
    __registryWriteOk = false;
    console.error(`\n${'='.repeat(60)}\n[registry] ⚠️ 回写后 YAML 严格解析失败，已放弃落盘（registry 与 SUMMARY 将失同步，必须手工回写！）\n  ${e.message.split('\n')[0]}\n${'='.repeat(60)}`);
    return;
  }
  fs.writeFileSync(file, text, 'utf-8');
  console.log(`[registry] 已自动回写 ${resultsToWrite.length} 个功能点 status/last_run/reason → registry/${id}.yaml`);
}

(async () => {
  if (!moduleId) { console.error('用法: node run.js <module> [--dry-run|--seed|--case <id>] | node run.js --cleanup <module>'); process.exit(1); }

  if (flags.has('--cleanup')) {
    await require('./data/cleanup')(moduleId);
    return;
  }
  if (flags.has('--seed')) {
    await require(`./data/factory/${moduleId}`)();
    return;
  }
  if (flags.has('--audit')) {
    // 收尾三对齐审计：纯文件操作不拉浏览器。
    // 规则：pass/fail 必须有 .case.js（可重放）与报告；blocked 必须有 reason；todo 不查。
    const reg = loadRegistry(moduleId);
    const feats = reg.pages.flatMap(p => p.features || []);
    const issues = [];
    for (const f of feats) {
      if (f.status === 'todo') continue;
      const hasCase = fs.existsSync(path.join(E2E, 'cases', moduleId, `${f.id}.case.js`));
      const hasReport = fs.existsSync(path.join(E2E, 'reports', moduleId, `${f.id}.md`));
      if ((f.status === 'pass' || f.status === 'fail') && !hasCase) issues.push(`${f.id} [${f.status}] 无用例文件（探索后漏固化，不可重放）`);
      if (!hasReport) issues.push(`${f.id} [${f.status}] 无报告文件`);
      if (f.status === 'blocked' && !f.reason) issues.push(`${f.id} [blocked] 无 reason（需五分类标签+解锁命令）`);
    }
    const audited = feats.filter(f => f.status !== 'todo').length;
    if (issues.length) {
      console.log(`[audit] ${moduleId} 三对齐审计：${audited} 个非 todo 功能点，不合规 ${issues.length} 项:`);
      issues.forEach(x => console.log(`  - ${x}`));
      process.exit(3);
    }
    console.log(`[audit] ${moduleId} 三对齐审计通过：${audited} 个非 todo 功能点（另有 todo ${feats.length - audited}）用例/报告/reason 齐全`);
    process.exit(0);
  }
  if (flags.has('--precheck')) {
    // 后端 SQL 链路预检 v2（表/列/函数三级 + 方言静扫）：纯 DB/文件操作不拉浏览器
    try {
      const { precheck } = require('./lib/precheck');
      const res = await precheck(moduleId, loadRegistry(moduleId), E2E, config);
      const tblTotal = res.tableRefs.size;
      const tblNote = res.dbSkipped ? `抽表 ${tblTotal} 张(DB未检)` : `抽表 ${tblTotal} 张：存在 ${res.present.length}，缺失 ${res.missing.length}`;
      console.log(`[precheck] mapper ${tblNote}；函数引用 ${res.funcRefs.size}，缺 ${res.missingFuncs.length}；缺列 ${res.missingCols.length}；方言 high ${res.dialectHigh.length}/warn ${res.dialect.length - res.dialectHigh.length}`);
      if (res.missing.length) {
        console.log('[precheck] ⚠ 缺失表（相关查询将呈 200+空/null 假成功，预判 blocked，勿直接造数）:');
        res.missing.forEach(t => console.log(`  - ${t} ← ${[...res.tableRefs.get(t)].join(', ')}`));
      }
      if (res.missingFuncs.length) {
        console.log('[precheck] ⚠ 缺失函数（命中 SQL 整条被吞）:');
        res.missingFuncs.forEach(f => console.log(`  - ${f} ← ${[...res.funcRefs.get(f)].join(', ')}`));
      }
      if (res.missingCols.length) {
        console.log('[precheck] ⚠ 缺失列（保守判定）:');
        res.missingCols.forEach(c => console.log(`  - ${c.table}.${c.col} ← ${c.file}`));
      }
      if (res.dialectHigh.length) {
        console.log('[precheck] ⚠ 高置信方言（目标 DB 必炸/必被吞）:');
        res.dialectHigh.forEach(d => console.log(`  - [${d.ruleId}] ${d.file}:${d.line} ${d.snippet.slice(0, 60)}`));
      }
      console.log(`[precheck] 报告: ${path.relative(E2E, res.reportFile)}`);
      if (res.dbSkipped) {
        console.error(`[precheck] ⚠ DB 通道不可用（${res.dbSkipped}）——静态方言段已落盘，表/列/函数存在性待通道恢复后重跑`);
        process.exit(2);
      }
      process.exit(res.ok ? 0 : 3);
    } catch (e) {
      console.error(`[precheck] 预检失败（非缺失项，是预检自身故障）: ${e.message}`);
      process.exit(2);
    }
  }

  const reg = loadRegistry(moduleId);
  const features = reg.pages.flatMap(p => p.features.map(f => ({ ...f, page: p })));

  const { browser, page } = await browserLib.launch({ headless: !flags.has('--headed') });
  const monitor = browserLib.attachMonitor(page);

  // 前端 preflight 探活：dev-server 崩溃/未起时 fail-fast，
  // 否则 login 与每个用例各自 30s 超时，误判为用例缺陷。
  const preOk = await session.frontendReachable(page);
  if (!preOk) {
    console.error(`Fatal: 前端未就绪（${session.BASE} 不可达）。dev-server 可能崩溃或未启动，`
      + `请先恢复前端服务，待 HTTP 200 后重跑。（环境故障：停下上报等恢复，禁止自行重启共享服务）`);
    await browser.close();
    process.exit(2);
  }
  await session.login(page);
  console.log('[run] 登录成功');

  if (flags.has('--dry-run')) {
    await session.gotoHash(page, reg.pages[0].route);
    const c = monitor.collect();
    console.log(`[dry-run] 导航 ${reg.pages[0].route} → url=${page.url()}`);
    // 路由挂载检测（可选，Vue 微前端项目开启）：URL 切换成功 ≠ 子应用挂载，
    // matched=0 即模块未注册（全模块白屏），提前报出免烧探针。
    if (config.vueRouteCheck) {
      const matched = await page.evaluate(() => {
        const vm = document.querySelector('#app') && document.querySelector('#app').__vue__;
        return vm && vm.$route ? vm.$route.matched.length : -1;
      }).catch(() => -1);
      if (matched === 0) {
        console.error(`[dry-run] ⚠ 路由未挂载（$route.matched=0）：${config.routeRegisterHint || '模块未注册进前端路由/子应用清单'}`);
      } else if (matched === -1) {
        console.log('[dry-run] 路由挂载检测不可用（__vue__ 不可达），跳过');
      }
    }
    console.log(`[dry-run] API失败 ${c.apiFailures.length}，豁免 ${c.exempted.length}，假成功嗅探 ${(c.swallowed || []).length}`);
    console.log(`[dry-run] 功能点清单（${features.length}）:`);
    features.forEach(f => console.log(`  - [${f.status}] ${f.id} ${f.name} (${f.level})`));
    await browser.close();
    return;
  }

  const runAll = flags.has('--all');
  // --all 保护终态 fail：带非空 reason 的 fail 是已定性发现（后端缺陷/产品缺陷/跨模块），
  // --all 回归重跑易被间歇结果覆写掉精编 reason。默认跳过，--rerun-fail 强制重跑。
  const rerunFail = flags.has('--rerun-fail');
  const isCuratedFail = f => f.status === 'fail' && f.reason && String(f.reason).trim();
  const targets = features.filter(f => {
    if (caseId) return f.id === caseId;                    // 显式单跑：无条件执行
    if (runAll) return f.status !== 'blocked' && !(isCuratedFail(f) && !rerunFail);
    return f.status !== 'pass';                             // 默认：执行 fail/blocked/todo
  });
  if (runAll) {
    const blocked = features.filter(f => f.status === 'blocked');
    const protectedFails = features.filter(f => isCuratedFail(f) && !rerunFail);
    console.log(`[all] 全量回归：执行 ${targets.length} 个功能点，跳过 blocked ${blocked.length} + 终态fail ${protectedFails.length}（前置未变/已定性；--rerun-fail 可强制重跑 fail）:`);
    blocked.forEach(f => console.log(`  - [blocked] ${f.id} ${f.name}`));
    protectedFails.forEach(f => console.log(`  - [fail·保护] ${f.id} ${f.name}（reason 已定性，跳过避免覆写）`));
  }
  const results = [];
  let exemptTotal = 0;
  // 案例级重试上限（环境类间歇抖动兜底）：仅对 fail 重试，重试成功才判 pass 并注记；
  // 持续失败仍 FAIL。默认 2 次额外尝试，可用 --retry N 覆盖。
  const RETRY = (() => { const i = argv.indexOf('--retry'); return i >= 0 && argv[i + 1] ? Math.max(0, parseInt(argv[i + 1], 10) || 0) : 2; })();

  // 单次执行：返回 result 对象（不写报告、不打印）
  async function runOnce(caseFile, f) {
    monitor.reset();
    const ctx = { page, monitor, actions, assert, session, feature: f, config };
    // 假成功嗅探摘要：去重同 URL+kind，只作观测输出不改判定
    const swallowNote = c => {
      if (!c.swallowed || !c.swallowed.length) return '';
      const uniq = [...new Set(c.swallowed.map(s => `${s.kind} ${s.url.replace(/^.*\/api\//, '')}`))];
      return `\n[假成功嗅探] ${uniq.length} 接口 HTTP200 但业务体异常（需甄别合法空 vs 吞错）:\n  ${uniq.slice(0, 10).join('\n  ')}${uniq.length > 10 ? `\n  …共${uniq.length}条` : ''}`;
    };
    try {
      const detail = await require(caseFile).run(ctx);
      const c = monitor.collect();
      return { featureId: f.id, name: f.name, level: f.level, status: 'pass', reason: '', detail: (detail || '') + swallowNote(c), exempted: c.exempted };
    } catch (e) {
      const c = monitor.collect();
      if (e.message.startsWith('BLOCKED:')) {
        return {
          featureId: f.id, name: f.name, level: f.level, status: 'blocked',
          reason: e.message.slice('BLOCKED:'.length).substring(0, 300), detail: swallowNote(c).trim(), exempted: c.exempted,
        };
      }
      return {
        featureId: f.id, name: f.name, level: f.level, status: 'fail',
        reason: e.message.substring(0, 200),
        detail: `JS错误: ${c.jsErrors.length}\nAPI失败: ${c.apiFailures.map(x => `${x.status} ${x.url.split('?')[0]} ${x.body || ''}`).join('\n')}` + swallowNote(c),
        exempted: c.exempted,
      };
    }
  }

  for (const f of targets) {
    const caseFile = path.join(E2E, 'cases', moduleId, `${f.id}.case.js`);
    if (!fs.existsSync(caseFile)) {
      console.log(`[skip] ${f.id} 无用例文件（待固化）`);
      continue;
    }
    let result = await runOnce(caseFile, f);
    let attempts = 1;
    // fail 才重试（blocked/pass 不重试）；重试成功注记「环境重试N次后通过」
    while (result.status === 'fail' && attempts <= RETRY) {
      console.log(`[retry ${attempts}/${RETRY}] ${f.id} 上轮 fail，间歇抖动兜底重试…`);
      await page.waitForTimeout(3000);
      const retryRes = await runOnce(caseFile, f);
      attempts++;
      if (retryRes.status !== 'fail') {
        retryRes.reason = retryRes.reason || `环境重试${attempts - 1}次后通过（首轮 fail 为服务间歇抖动，非页面缺陷）`;
        retryRes.detail = `[环境重试${attempts - 1}次转 ${retryRes.status}]\n` + (retryRes.detail || '');
        result = retryRes;
        break;
      }
      result = retryRes;
    }
    exemptTotal += (result.exempted || []).length;
    if (result.status === 'fail') {
      const shot = path.join(E2E, 'reports', moduleId, `${f.id}-fail.png`);
      fs.mkdirSync(path.dirname(shot), { recursive: true });
      await page.screenshot({ path: shot, fullPage: true }).catch(() => {});
      result.screenshots = [`${f.id}-fail.png`];
    }
    const file = report.writeFeature(moduleId, result);
    console.log(`[${result.status.toUpperCase()}] ${f.id} ${result.reason || ''} → ${path.relative(E2E, file)}`);
    results.push(result);
  }
  if (results.length) {
    // 自动回写 registry（--case 单跑也回写，保证终态不漏）
    writeBackRegistry(moduleId, results);
  }
  if (!caseId && results.length) {
    // SUMMARY 从 registry 终态聚合：本轮执行过的用本轮结果，
    // 未执行的用回写后的 registry 终态补齐（注明来源）。
    const regAfter = loadRegistry(moduleId);
    const ranIds = new Set(results.map(r => r.featureId));
    const fullResults = regAfter.pages.flatMap(p => p.features).map(f => {
      if (ranIds.has(f.id)) return results.find(r => r.featureId === f.id);
      return {
        featureId: f.id, name: f.name, level: f.level, status: f.status,
        reason: f.status === 'blocked' ? 'registry 终态（本轮未执行，根因见 registry 执行注/pending-issues）'
          : (f.status === 'pass' ? 'registry 终态（本轮未执行）' : ''),
        detail: '', exempted: [],
      };
    }).filter(r => r.status !== 'todo');
    const s = report.writeSummary(moduleId, reg.name, fullResults, { exemptTotal });
    console.log(`[SUMMARY] ${path.relative(E2E, s)}（含 registry 终态补齐，共 ${fullResults.length} 行）`);
  }
  // 总账 modules.yaml 严格校验（收尾常手工编辑，尾逗号/多行/嵌套引号易炸 js-yaml 审计工具，
  // run.js 本身不写它但审计依赖它——只读告警不阻断本模块回写）。
  try {
    yaml.load(fs.readFileSync(path.join(E2E, 'registry', 'modules.yaml'), 'utf-8'));
  } catch (e) {
    __registryWriteOk = false;
    console.error(`[modules.yaml] ⚠️ 总账严格解析失败（不影响本模块回写，但会废掉总账审计，请修）: ${e.message.split('\n')[0]}`);
  }
  await browser.close();
  const failExit = results.some(r => r.status === 'fail') ? 1 : 0;
  process.exit(!__registryWriteOk ? 3 : failExit);
})().catch(e => { console.error('Fatal:', e); process.exit(2); });
