# REFERENCE — 检测层与 e2e Harness

主 `SKILL.md` 的补充专题：可直接改造的检测器骨架、`wxt.config` 基线、mock 站点 + Chrome-for-Testing e2e harness、合规检查清单。所有代码均从生产交付脱敏泛化而来，用时把站点特定常量（host、路径正则、字段名）替换为你的目标。

## 1. 多通道检测器骨架（纯函数 + 可注入）

关键设计：把检测器做成**不依赖浏览器**的纯函数，环境通过参数注入，这样单测无需 headless。

```ts
// utils/detect.ts
export interface AssetInfo {
  id: number | string;
  title: string;
  fileUrl: string;       // 最终可下载 URL
  thumbUrl?: string;
  status: string;
}

// 可注入环境：pathname / DOM scripts 文本 / performance entries / fetch
export interface DetectEnv {
  pathname: string;
  scripts: Array<{ textContent: string | null }>;
  entries: ReadonlyArray<{ name: string }>;
  fetcher?: typeof fetch;
}

// 从 <script> 文本里用「括号匹配」抠出 SSR 注入的 JSON 对象（比正则稳）
export function extractInjectedData(
  scripts: Array<{ textContent: string | null }>,
  marker = 'initialData',      // 目标字段名
  pushToken = '__next_f',      // 框架注入令牌
): Record<string, unknown> | null {
  for (const s of scripts) {
    const t = s.textContent;
    if (!t || !t.includes(pushToken) || !t.includes(marker)) continue;
    // 放宽 chunk 类型：push([<任意数字>, "<json 字符串>"])
    for (const m of t.matchAll(/\.push\(\[\d+,("(?:[^"\\]|\\.)*")\]\)/gs)) {
      let chunk: string;
      try { chunk = JSON.parse(m[1]); } catch { continue; }
      const idx = chunk.indexOf(`"${marker}":`);
      if (idx < 0) continue;
      const start = chunk.indexOf('{', idx);
      if (start < 0) continue;
      let depth = 0, inStr = false, esc = false;
      for (let i = start; i < chunk.length; i++) {
        const c = chunk[i];
        if (inStr) { if (esc) esc = false; else if (c === '\\') esc = true; else if (c === '"') inStr = false; continue; }
        if (c === '"') inStr = true;
        else if (c === '{') depth++;
        else if (c === '}' && --depth === 0) {
          try { return JSON.parse(chunk.slice(start, i + 1)); } catch { return null; }
        }
      }
    }
  }
  return null;
}

// 按可靠性排序，命中第一个即返回
export async function detect(env: DetectEnv): Promise<AssetInfo | null> {
  // 通道 1：SSR 注入初始状态（最稳，登出态也有效）
  const injected = extractInjectedData(env.scripts);
  if (injected && typeof injected.file_url === 'string') {
    return { id: Number(injected.id ?? 0), title: String(injected.title ?? 'asset'),
             fileUrl: injected.file_url, status: String(injected.status ?? 'complete') };
  }
  // 通道 2：由路径标识符构造 URL（无需页面数据）
  const m = /^\/e\/([a-f0-9]{32})\/?$/.exec(env.pathname);
  if (m) return { id: 0, title: `asset-${m[1].slice(0, 8)}`,
                  fileUrl: buildPublicUrl(m[1]), status: 'complete' };
  // 通道 3：同源 API（登录态，携带凭据）
  for (const id of collectIds(env.entries).reverse()) {
    try { return await fetchDetail(id, env.fetcher ?? fetch); } catch { /* 下一个 */ }
  }
  // 通道 4：被动图床兜底
  const url = collectAssetUrls(env.entries).at(-1);
  return url ? { id: 0, title: 'asset', fileUrl: url, status: 'complete' } : null;
}
```

单测要点：喂合成 `scripts`/`entries`/`pathname`，断言通道优先级、去重、`!res.ok` 错误路径、文件名清洗、登出态零匹配。

## 2. wxt.config 基线（最窄权限）

```ts
// wxt.config.ts
import { defineConfig } from 'wxt';
export default defineConfig({
  modules: ['@wxt-dev/module-vue'],
  manifest: {
    name: '<Your Extension>',
    description: '<one line>',
    permissions: ['downloads'],                 // 仅声明必需
    host_permissions: ['*://target.example.com/*'], // 具体 host，禁用 <all_urls>
  },
});
```

下载走 background（content script 跨域受限）：

```ts
// entrypoints/background.ts
browser.runtime.onMessage.addListener((msg) => {
  if (msg?.type === 'download') {
    return browser.downloads.download({ url: msg.url, filename: sanitize(msg.title) + '.jpg' });
  }
});
export function sanitize(name: string): string {
  return (name.replace(/[\\/:*?"<>|]/g, '_').trim()) || 'asset';
}
```

## 3. mock 站点 + Chrome-for-Testing e2e Harness

e2e 目标：**真实浏览器加载真实构建产物**，跑通「检测→注入→点击→下载」并断言**字节级一致**。

### 3.1 mock 站点（复现每种页面类型）

```js
// e2e/mock-site.mjs — 极小 HTTP 服务
import http from 'node:http';
export const PORT = 18777;
export const EMBED_HASH = 'abcdef0123456789abcdef0123456789';
function embedPage(hash) {
  // SSR 注入 payload，与真实页面同构
  const payload = `1:["$","$L1",null,{"initialData":{"id":1,"title":"Mock","status":"complete","file_url":"http://127.0.0.1:${PORT}/asset.jpg"}}]`;
  return `<!doctype html><html><body><img src="/asset.jpg"/>
    <script>self.__next_f=self.__next_f||[];self.__next_f.push([1,${JSON.stringify(payload)}]);</script>
    </body></html>`;
}
export function startMockSite() {
  const server = http.createServer((req, res) => {
    const u = new URL(req.url, `http://127.0.0.1:${PORT}`);
    if (u.pathname === `/e/${EMBED_HASH}`) { res.end(embedPage(EMBED_HASH)); }
    else if (u.pathname === '/api/proxy') { res.setHeader('content-type','application/json');
      res.end(JSON.stringify({ request: { id: 1, title: 'Mock', status: 'complete',
        file_url: `http://127.0.0.1:${PORT}/asset.jpg` } })); }
    else if (u.pathname === '/asset.jpg') { res.setHeader('content-type','image/jpeg'); res.end(ASSET_BYTES); }
    else { res.statusCode = 404; res.end('not found'); }
  });
  return new Promise((r) => server.listen(PORT, '127.0.0.1', () => r(server)));
}
```

### 3.2 CfT 加载扩展（关键：不是系统 Chrome）

```js
// e2e 中用 Chrome for Testing，因为 Chrome 137+ 品牌版已移除 --load-extension
import puppeteer from 'puppeteer-core';
import { readdirSync, existsSync } from 'node:fs';
import { join } from 'node:path';

function findChromeForTesting() {
  if (process.env.CHROME_PATH) return process.env.CHROME_PATH;
  // Playwright 缓存的 chromium 也可用
  const pwDir = `${process.env.HOME}/.cache/ms-playwright`;
  const cands = readdirSync(pwDir).filter((d) => /^chromium-\d+$/.test(d))
    .sort((a, b) => Number(b.split('-')[1]) - Number(a.split('-')[1]))
    .map((d) => join(pwDir, d, 'chrome-linux64', 'chrome')).filter(existsSync);
  if (cands.length) return cands[0];
  throw new Error('need Chrome for Testing (not branded Chrome 137+)');
}

const browser = await puppeteer.launch({
  executablePath: findChromeForTesting(),
  headless: false,                       // 扩展需要非 headless
  args: [
    `--load-extension=${EXT_PATH}`,      // EXT_PATH = .output/chrome-mv3
    `--disable-extensions-except=${EXT_PATH}`,
    `--user-data-dir=${TMP_PROFILE}`,
    '--no-sandbox', '--disable-gpu',
  ],
});
// MV3：等 service worker target，而非 background page
const swTarget = await browser.waitForTarget((t) => t.url().includes('background.js'), { timeout: 15000 });
```

运行：`xvfb-run -a node e2e/run-e2e.mjs`（headless Linux 需虚拟显示器）。

### 3.3 字节级断言

```js
const served = ASSET_BYTES;                    // mock 服务返回的原始字节
const downloaded = readFileSync(downloadedPath);
assert(Buffer.compare(served, downloaded) === 0, 'download must be byte-identical');
```

## 4. 合规检查清单（擦边/双用途工具务必逐项过）

- [ ] 只保存用户**自己账号**下、浏览器**已加载**的内容
- [ ] 只走平台**自己公开**的服务端点，不破解 / 不绕过付费墙 / 不访问 premium 专属资源
- [ ] 任何"去水印/裁剪"类处理是**纯本地**操作，作用于用户已合法获得的内容
- [ ] 声明**最窄**权限与具体 host，不用 `<all_urls>`
- [ ] 登出态 / 无权限资源产出**零**匹配（不误注入、不误导出）
- [ ] 开源时的免责与许可交给 `devlab-github-oss-ops`（educational use / not affiliated / takedown / 内容许可）
