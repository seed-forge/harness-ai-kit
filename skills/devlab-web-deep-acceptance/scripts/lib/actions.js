/**
 * lib/actions.js — 通用 UI 原语占位（最小集）。
 * 项目组件库专属原语（树选择/级联下拉/弹窗操作）放项目侧 cases/<module>/_helpers.js，
 * 不进框架库。这里只收与组件库无关的浏览器级操作。
 */

/** 按文本点击可见按钮（精确文本，避免同名按钮撞车） */
async function clickButton(page, text, { timeout = 8000 } = {}) {
  const btn = page.locator(`button:visible`, { hasText: new RegExp(`^\\s*${text}\\s*$`) }).first();
  await btn.click({ timeout });
}

/** 等待 toast/提示出现并读取文案（toast duration 可能仅 ~1s，click 后 ≤400ms 内读） */
async function readToast(page, selector = '.el-message:visible, .toast:visible', { timeout = 2000 } = {}) {
  const loc = page.locator(selector).last();
  await loc.waitFor({ state: 'visible', timeout }).catch(() => {});
  return (await loc.innerText().catch(() => '')).trim();
}

module.exports = { clickButton, readToast };
