/**
 * lib/session.js — 登录会话管理（通用化版）。
 *
 * 默认实现：表单登录（page.evaluate 填值 + dispatchEvent input 触发框架响应式 → 点击登录）。
 * 适配点：
 *  - 选择器/凭据走 e2e.config.js 的 login 段；
 *  - 前端加密（AES 等）无需在 e2e 侧实现——走浏览器 UI 由前端 JS 自动完成；
 *  - SSO/OAuth/Token 项目：重写 login() 为"注入 storage/token"或走 IdP 登录流；
 *  - 账号锁定防护（如 DB 侧解锁）：按项目加 ensureAccountUnlocked() 前置 hook。
 */
const path = require('path');
const config = require(path.join(__dirname, '..', 'e2e.config.js'));

const BASE = config.baseUrl;
const L = config.login || {};

/**
 * 表单登录（失败重试）。
 * Vue/React 响应式：直接设 input.value 无效，必须 dispatchEvent(new Event('input',{bubbles:true}))。
 */
async function login(page, { retries = 3 } = {}) {
  let lastErr;
  for (let i = 1; i <= retries; i++) {
    try {
      await page.goto(`${BASE}/${L.hash || '#/login'}`, { waitUntil: 'networkidle', timeout: 30000 });
      await page.waitForSelector(L.userSelector, { timeout: 10000 });
      await page.evaluate(([u, p, us, ps]) => {
        const ui = document.querySelector(us);
        const pi = document.querySelector(ps);
        ui.value = u; ui.dispatchEvent(new Event('input', { bubbles: true }));
        pi.value = p; pi.dispatchEvent(new Event('input', { bubbles: true }));
      }, [L.user, L.pass, L.userSelector, L.passSelector]);
      await page.waitForTimeout(500);
      await page.click(L.submitSelector);
      await page.waitForFunction(() => !location.hash.includes('login'), null, { timeout: 20000 });
      return true;
    } catch (e) {
      lastErr = e;
      console.warn(`[session] 登录第 ${i}/${retries} 次失败: ${e.message}`);
    }
  }
  throw new Error(`登录失败（${retries} 次）: ${lastErr.message}`);
}

/** 导航到 hash 路由并等待网络空闲 */
async function gotoHash(page, hash, { waitMs = 4000 } = {}) {
  await page.goto(`${BASE}/${hash}`, { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(waitMs);
}

/** 导出登录态存储内容（供 data factory 提取 token 用） */
async function dumpStorage(page) {
  return page.evaluate(() => ({
    local: { ...localStorage },
    session: { ...sessionStorage },
    cookie: document.cookie,
  }));
}

/**
 * 前端探活：baseUrl 是否可达。仅发一次轻量 goto，
 * 连上且非 5xx 即算就绪（不等 networkidle，避免慢）。供 run.js preflight 用。
 * 崩溃时 goto 抛 ERR_CONNECTION_REFUSED → 返回 false，让上层 fail-fast。
 */
async function frontendReachable(page, { timeout = 10000 } = {}) {
  try {
    const resp = await page.goto(BASE, { waitUntil: 'domcontentloaded', timeout });
    return !!resp && resp.status() < 500;
  } catch (e) {
    return false;
  }
}

module.exports = { BASE, login, gotoHash, dumpStorage, frontendReachable };
