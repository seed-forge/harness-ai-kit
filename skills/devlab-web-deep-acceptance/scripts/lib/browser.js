/**
 * lib/browser.js — 浏览器封装（通用化版）：控制台/网络监听，已知间歇错误豁免（豁免仍计数，写入报告）。
 * 豁免表/噪声表/嗅探 URL 全部从 e2e.config.js 读，按项目配置。
 */
const path = require('path');
const { chromium } = require('playwright');
const config = require(path.join(__dirname, '..', 'e2e.config.js'));

// 豁免规则：URL 命中且同 URL 稍后出现 2xx（重试成功）→ 记豁免不记失败
const EXEMPT_RETRY_PATTERNS = config.exemptRetryPatterns || [];
// 纯噪声：直接忽略，不参与判定
const NOISE_PATTERNS = config.noisePatterns || [/sockjs-node/, /favicon/, /\.(js|css|woff2?|ttf|png|ico)(\?|$)/];

// 假成功嗅探：HTTP 2xx 但业务 body 异常（code!=成功码 或 result:null）。只嗅探
// config.businessApiPattern 匹配的 JSON 响应；结果作为 collect() 新增维度 swallowed 暴露，
// **不计入 apiFailures、不改变任何既有判定**（result:null 对部分写接口是合法空返回，
// 由用例/执行注结合语义判读）。
const SWALLOW_SNIFF_URL = config.businessApiPattern || /\/api\//;
const BIZ_OK = String(config.bizSuccessCode || '200');
const SWALLOW_MAX_ENTRIES = 200;      // 防长会话内存膨胀

async function launch({ headless = true } = {}) {
  const browser = await chromium.launch({ headless });
  const page = await browser.newPage();
  return { browser, page };
}

/**
 * 挂载监听器。返回 { reset, collect }。
 * collect() => { jsErrors, apiFailures, exempted, swallowed }
 *  - jsErrors: 页面 console error / pageerror（噪声除外）
 *  - apiFailures: HTTP >= 400（命中豁免且重试成功者除外）
 *  - exempted: 命中豁免表且同路径稍后 2xx 的（重试成功才豁免，仍计数）
 *  - swallowed: HTTP 2xx 但业务体异常（code!=成功码/result:null），只观测不改判定
 */
function attachMonitor(page) {
  let jsErrors = [];
  let apiFailures = [];
  let exempted = [];
  let swallowed = [];
  const pendingByPath = new Map(); // path → 最近非2xx记录（等重试成功核销）

  const isNoise = (url) => NOISE_PATTERNS.some(re => re.test(url));

  page.on('console', msg => {
    if (msg.type() === 'error') jsErrors.push(msg.text().slice(0, 300));
  });
  page.on('pageerror', e => jsErrors.push(String(e).slice(0, 300)));

  page.on('response', res => {
    const url = res.url();
    if (isNoise(url)) return;
    const status = res.status();
    const pathKey = url.split('?')[0];
    if (status >= 400) {
      pendingByPath.set(pathKey, { status, url });
      return;
    }
    // 2xx：先核销豁免
    if (pendingByPath.has(pathKey)) {
      const prev = pendingByPath.get(pathKey);
      pendingByPath.delete(pathKey);
      if (EXEMPT_RETRY_PATTERNS.some(re => re.test(prev.url))) {
        exempted.push({ status: prev.status, url: prev.url });
      } else {
        apiFailures.push({ status: prev.status, url: prev.url, body: '' });
      }
    }
    // 假成功嗅探（仅业务 API 的 JSON 响应）
    if (SWALLOW_SNIFF_URL.test(url) && swallowed.length < SWALLOW_MAX_ENTRIES) {
      const ct = (res.headers()['content-type'] || '');
      if (!/json/.test(ct)) return;
      res.json().then(b => {
        if (b == null || typeof b !== 'object') return;
        const code = b.code != null ? String(b.code) : null;
        if (code != null && code !== BIZ_OK) {
          swallowed.push({ kind: `biz-code:${code}`, url: url.slice(0, 200) });
        } else if (!('result' in b) || b.result == null) {
          swallowed.push({ kind: 'null-result', url: url.slice(0, 200) });
        }
      }).catch(() => {});
    }
  });

  return {
    reset() { jsErrors = []; apiFailures = []; exempted = []; swallowed = []; pendingByPath.clear(); },
    collect() {
      // 收尾：pendingByPath 中未被 2xx 核销的进 apiFailures
      for (const [, v] of pendingByPath) apiFailures.push({ status: v.status, url: v.url, body: '' });
      pendingByPath.clear();
      return { jsErrors, apiFailures, exempted, swallowed };
    },
  };
}

module.exports = { launch, attachMonitor };
