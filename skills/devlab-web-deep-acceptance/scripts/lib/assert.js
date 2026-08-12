/**
 * lib/assert.js — 断言库（通用化版）：失败抛 AssertionError，由 run.js 捕获记入报告。
 * 表格选择器从 e2e.config.js selectors 段读（按项目组件库配置）。
 */
const path = require('path');
const config = require(path.join(__dirname, '..', 'e2e.config.js'));
const SEL = config.selectors || { tableBodyRows: '.el-table__body tbody tr' };

class AssertionError extends Error {}

function ok(cond, msg) { if (!cond) throw new AssertionError(msg); }

/** 硬条件1：不报错（基于 monitor.collect() 结果） */
function noErrors(collected) {
  ok(collected.jsErrors.length === 0, `JS 错误 ${collected.jsErrors.length} 个: ${collected.jsErrors[0] || ''}`);
  ok(collected.apiFailures.length === 0,
    `API 失败 ${collected.apiFailures.length} 个: ${collected.apiFailures.map(f => `${f.status} ${f.url.split('?')[0]}`).slice(0, 3).join('; ')}`);
}

/** 硬条件2：表格行数 ≥ min */
async function tableHasRows(page, min = 1) {
  const rows = await page.$$(SEL.tableBodyRows);
  ok(rows.length >= min, `表格行数 ${rows.length} < ${min}`);
  return rows.length;
}

/** 硬条件3：表格前 n 行指定列无空值/字面量脏值 */
async function tableCellsNotEmpty(page, maxRows = 5) {
  const bad = await page.evaluate(({ sel, max }) => {
    const rows = [...document.querySelectorAll(sel)].slice(0, max);
    const out = [];
    rows.forEach((tr, ri) => [...tr.querySelectorAll('td .cell, td')].forEach((td, ci) => {
      const t = td.textContent.trim();
      if (['null', 'undefined', 'NaN'].includes(t)) out.push(`行${ri + 1}列${ci + 1}="${t}"`);
    }));
    return out;
  }, { sel: SEL.tableBodyRows, max: maxRows });
  ok(bad.length === 0, `脏值: ${bad.join(', ')}`);
}

/** 某行文本存在/不存在于表格 */
async function rowExists(page, text, expected = true) {
  const sel = SEL.tableRowByText ? SEL.tableRowByText(text) : `${SEL.tableBodyRows}:has-text("${text}")`;
  const n = await page.locator(sel).count();
  ok(expected ? n > 0 : n === 0, `行"${text}"${expected ? '不存在' : '仍存在'}（匹配 ${n}）`);
}

/** 当前 hash 包含片段（跳转断言） */
function urlContains(page, fragment) {
  ok(page.url().includes(fragment), `URL 不含 "${fragment}": ${page.url()}`);
}

/**
 * opt-in 硬条件：无"接口层假成功"（HTTP200+code:失败 / result:null）。
 * monitor.collect().swallowed 是纯增强维度，默认不进 apiFailures、noErrors 不检查它——
 * 因为 result:null 对部分写接口是合法空。**依赖查询结果的用例（L2/L3/L4）应显式调用
 * 本断言**，否则会在 code:500-in-200 上误判 PASS。
 * @param opts.ignore 正则或 (entry)=>bool，命中则忽略（如已知合法空返回的写接口 URL）
 * @param opts.kinds 只对指定形态告警，默认 ['biz-code:'] 前缀 + 'null-result'
 */
function noSwallowedErrors(collected, { ignore, kinds } = {}) {
  const sw = (collected.swallowed || []).filter(e => {
    if (ignore) {
      if (typeof ignore === 'function' && ignore(e)) return false;
      if (ignore instanceof RegExp && ignore.test(e.url)) return false;
    }
    if (kinds && kinds.length) return kinds.some(k => e.kind.startsWith(k));
    return true;
  });
  ok(sw.length === 0,
    `接口层假成功 ${sw.length} 个（HTTP200 但业务失败，非真空数据）: ` +
    sw.map(e => `${e.kind} ${e.url}`).slice(0, 3).join('; '));
}

module.exports = { AssertionError, ok, noErrors, noSwallowedErrors, tableHasRows, tableCellsNotEmpty, rowExists, urlContains };
