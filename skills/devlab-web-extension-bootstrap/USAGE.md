# DevLab Web Extension Bootstrap — Usage

## 何时用

要从零做一个浏览器扩展，尤其是"从某个 Web 应用里提取/下载/增强内容"的扩展时。它固化了检测层逆向、WXT+Vue+MV3 选型、三面架构、真实浏览器 e2e 的完整方法论，让你不再重复踩坑。

## 前置条件

- Node ≥ 20（`nvm use 22`）、pnpm
- e2e 需要 Chrome for Testing（或 Playwright 的 chromium）+ Linux 上的 `xvfb`

## 可直接复制的中文 Prompt

```
用 devlab-web-extension-bootstrap 技能，帮我做一个浏览器扩展：
目标站点是 <URL>，我要导出/增强的内容是 <内容>。
请先按 §1 确认可行性与需覆盖的页面类型，再按 §2 逆向出数据通道并实现可注入的纯函数检测器（先写单测），
然后 WXT+Vue+MV3 脚手架、最窄权限，搭 content/background/popup 三面，
最后用 mock 站点 + Chrome for Testing 跑字节级一致的 e2e，并在真实站点探测验证。
代码就绪后交给 devlab-github-oss-ops 做开源与发布。
```

## 产出

- 可加载的 MV3 扩展 + 纯函数检测层 + 单测 + e2e 闭环
- 交接 `devlab-github-oss-ops` 的就绪代码
