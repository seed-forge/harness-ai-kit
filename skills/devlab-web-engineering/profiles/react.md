# React Profile（模板级）

> 定位：模板级骨架（对应 srv-engineering 的简化版 profile）。当前无实证项目深度，
> 提供六域基础工作流与迁移要点；后续有实证再加深。

## 适用判定

`package.json` 含 `react` / `react-dom` / `next`，或用户显式指定 `framework=react`。
语言基线默认 TypeScript。

## 六域工作流（精简版）

### 域 1：Project Bootstrap

- 新项目：`npm create vite@latest`（Vite + React + TS 官方模板）
- Next.js：`npx create-next-app@latest`
- CRA 存量：react-scripts 保留或迁移 Vite（见域 2）
- 生成物同 vue profile（scripts/*.template 复用）

### 域 2：Build

- Vite 主线：`vite build`；Next.js：`next build`
- CRA → Vite 迁移 checklist：
  1. 移除 react-scripts，加 vite + @vitejs/plugin-react
  2. index.html 移到根目录 + `<div id="root">`
  3. env 前缀 REACT_APP_ → VITE_
  4. 路径别名 jsconfig/tsconfig paths → vite resolve.alias
  5. 验证构建产物

### 域 3：Dependency

- 同 vue profile：锁文件强制、增量安装、循环依赖检测

### 域 4：Packaging

- dist/ 静态产物；SPA history fallback（nginx `try_files`）
- Next.js 服务端渲染产物按框架官方部署方式（node server 或静态导出）

### 域 5：Runtime/Environment

- Node 版本管理 / 端口策略 / registry 降级：同 vue profile（跨框架，见 references/）
- env 前缀：VITE_ / NEXT_PUBLIC_

### 域 6：Engineering Convention

- TS 严格模式 + ESLint（eslint-plugin-react-hooks）+ Prettier
- 组件工程结构：colocation（组件/样式/测试同目录）

## 引用

- `profiles/react/REFERENCE-REACT.md` — React 项目特定配置（web-bootstrap 迁移）
- `references/REFERENCE-BUILD-TOOLS.md` — Vite/Next 构建要点
- 其他框架（angular/next/nuxt）：references 引用层，不建空壳 profile
