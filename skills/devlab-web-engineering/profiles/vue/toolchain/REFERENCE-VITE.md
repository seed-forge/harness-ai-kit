# Vite 工具链（主线）

> 从 `references/REFERENCE-BUILD-TOOLS.md` 拆分的 Vite 专属层；完整跨框架对比见原文件。

## 新项目默认

- Vue3: `npm create vue@latest`（含 TS/JSX/Router/Pinia 选项）
- 框架无关: `npm create vite@latest`

## 关键配置（vite.config.ts）

```ts
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  base: '/',                    // 微前端子应用改 '/sub-app/'
  server: { host: true, port: 21010 },
  resolve: { alias: { '@': '/src' } },
  build: { chunkSizeWarningLimit: 1024 }
})
```

## 环境变量

- 前缀 `VITE_`；`import.meta.env.VITE_API_BASE_URL`
- 模式文件：.env.development / .env.production / .env.test（--mode test）

## 微前端集成

- 子应用 `base: '/sub-app/'`；qiankun entry 指向 dev server
- 公共依赖 externals 配置防多实例

## 常用命令

```bash
pnpm dev          # vite --port $PORT --host
pnpm build        # vite build --mode production
pnpm preview      # 本地预览产物
```
