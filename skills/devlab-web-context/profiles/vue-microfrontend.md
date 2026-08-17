# PROFILE：vue-microfrontend — Vue2 微前端子类型（实战级）

> 实证来源：Vue2 微前端 lerna monorepo（shell + 微框架内核 + N 个业务子应用）。
> 本文件迁移自 `devlab-context-bootstrap` 的 `REFERENCE-ADAPTER-frontend-web.md`（v0.1.1 → devlab-web-context v0.1.0）。

## 判定信号

命中以下任一即判定为本子类型：
- deps 含 `qiankun` / `micro-app` / 自研 shell 注册配置
- 项目含主应用 + 子应用结构（`src/apps/*`、`subapp-*` 目录、lerna packages 含多个可运行包）
- env 含模块注册清单类变量（如 `VUE_APP_MODULES`）

## 扫描信号表（9 项）

| 维度 | 信号文件/命令 | 提取什么 |
|------|--------------|----------|
| 框架 | `package.json` deps | vue/react/angular 及版本；vue-router/vuex/redux |
| 构建工具 | `vite.config.*` / `vue.config.js` / `webpack.config.*` | 构建链、dev server 配置、proxy 配置 |
| 包管理 | `pnpm-lock.yaml` / `yarn.lock` / `package-lock.json` / `lerna.json` | 包管理器；monorepo 工具（lerna/turbo/pnpm workspace） |
| Node 版本 | `package.json engines` / `.nvmrc` / dev 脚本内 PATH 注入 | 版本要求；多版本并存时各用途版本 |
| 环境变量 | `.env*`（含 .local 变体）+ `.env.local.example` | API base、功能开关、模块注册清单类变量 |
| 微前端 | `qiankun`/`micro-app`/自研 shell 的注册配置 | 子应用注册方式（构建期/运行时）、子应用清单来源 |
| 组件库 | deps + `src/components`/`ui-components` | 是否二开换肤（DOM 前缀≠官方文档，深度验收陷阱 1） |
| 部署 | `Jenkinsfile`/`deploy*.sh`/nginx conf | 产物形态（dist 静态文件）、部署目标、回滚方式 |
| 后端接入 | dev proxy 配置 / 网关路由规范 | 前端→网关→服务的完整链路（与后端台账呼应） |

## 特有条目（通用五维之外必查，写入画像键）

1. **dev server 台账**（`dev_server` 键）：启动命令（实证：多有 dev.sh 封装）、端口、Node 版本要求、常见崩溃模式（实证：node 堆 OOM errno 134）与处置规则（禁止会话自行重启共享 dev server）。
2. **运行时模块注册**（`module_registry` 键）：微前端项目的子应用清单来自 env 变量或注册配置（实证：`VUE_APP_MODULES` 数组决定哪些子应用路由被挂载）——未注册=白屏无报错，这是前端台账独有的高价值条目。
3. **dev proxy / API 前缀**（`dev_proxy` 键）：开发态代理到哪个网关/后端；业务 API 前缀模式（如 `/emas/ms/`），响应业务码约定（如 code=200 为成功）——直接决定 e2e 的 e2e.config.js 取值。
4. **路由模式**（`routing` 键）：hash / history；微前端下跨子应用导航的约束（hash 导航脏状态需真 reload）。
5. **构建与部署形态**（`build_deploy` 键）：构建产物目录、静态资源路径（publicPath）、nginx 托管还是嵌入后端、环境隔离用 `.env.local` 而非 Spring Profile。
6. **组件库契约**（`component_library` 键）：官方库还是二开（二开必须记录真实 DOM 前缀与源码位置）；全局组件（左树/门户栅格/消息框）的使用约束。

## 与后端台账的差异（写画像/文档时注意）

| 维度 | 后端 | 前端 |
|------|------|------|
| 环境隔离 | Spring Profile | `.env.local` + 构建时注入 |
| 日志 | 文件（Logback） | Console + 浏览器 devtools |
| 部署 | JAR + 进程管理 | 静态产物 + nginx/CDN |
| 排障入口 | 服务日志 | dev server 输出 + 网络面板 + console |
| "服务状态" | 进程/端口 | dev server 可达性 + 子应用注册状态 |

## 常见误判

- 把 frontend-web 项目当 backend-nodejs 写台账（有 package.json 不等于 Node 服务）——判定看 deps。
- 漏掉运行时注册清单类 env 变量（只抄 `.env.example` 的常规项）。
- dev proxy 目标写"后端地址"一笔带过——必须写清网关路由规范与业务码约定。
- monorepo 只扫根 package.json，漏子应用各自 dev server 与端口。
