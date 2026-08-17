# PROFILE：react-spa — React SPA 子类型（骨架级）

> 模板级：信号表 + 骨架已就位，待实战回填升级（对齐 `profiles/vue-microfrontend.md` 的实证深度）。

## 判定信号

- deps 含 `react` + `react-dom`，无微前端注册配置（qiankun/micro-app/自研 shell）
- 存在 `src/App.*`、`src/index.*`，无多子应用结构

## 扫描信号表（通用 9 项对齐 REFERENCE-WEB-RULES）

| 维度 | 信号文件/命令 | 提取什么 |
|------|--------------|----------|
| 框架 | `package.json` deps | react/react-dom 版本；react-router/react-redux/zustand |
| 构建工具 | `vite.config.*` / `webpack.config.*` / CRA 配置 | 构建链、dev server、proxy |
| 包管理 | 锁文件 | pnpm/yarn/npm |
| Node 版本 | `engines` / `.nvmrc` | 版本要求 |
| 环境变量 | `.env*` + `.env.local.example` | `REACT_APP_`/`VITE_` 前缀变量 |
| 微前端 | 无（骨架位：未来可能嵌入 qiankun 子应用） | — |
| 组件库 | deps + `src/components` | antd/MUI 等；是否二开 |
| 部署 | CI/nginx conf | 静态产物 + 托管方式 |
| 后端接入 | dev proxy / 网关路由 | API 前缀与业务码约定 |

## 特有条目（待实战回填）

- [ ] dev server 台账（启动命令/端口/崩溃模式）
- [ ] 运行时配置（env 注入项、feature flag）
- [ ] dev proxy / API 前缀与业务码约定
- [ ] 路由模式（react-router 版本差异：v5 vs v6）
- [ ] 构建与部署形态（SPA fallback 路由、publicPath）
- [ ] 组件库契约（是否二开）

## 常见误判（占位，待实证补充）

- 将 Next.js SSR 项目误判为 react-spa（有 `next dev` 脚本的是 next 子类型，本 profile 不覆盖）。
