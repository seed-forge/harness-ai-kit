# REFERENCE-WEB-RULES — 跨子类型通用 Web 扫描规则

> 所有前端子类型（vue-microfrontend / react-spa / 未来 next、angular 等）共用的信号与扫描方法。
> 子类型差异在 `profiles/<type>.md`，这里只放跨类型通用项。

## 通用信号（所有 web 项目必扫）

| 维度 | 信号文件/命令 | 提取什么 |
|------|--------------|----------|
| 框架 | `package.json` deps | 前端框架及版本；路由/状态库 |
| 构建工具 | `vite.config.*` / `vue.config.js` / `webpack.config.*` / `next.config.*` | 构建链、dev server、proxy |
| 包管理 | `pnpm-lock.yaml` / `yarn.lock` / `package-lock.json` / `lerna.json` / `pnpm-workspace.yaml` | 包管理器；monorepo 工具 |
| Node 版本 | `engines` / `.nvmrc` / dev 脚本 | 版本要求；多版本并存场景 |
| 环境变量 | `.env*` + `.env.local.example` | API base、feature flag、框架前缀（VUE_APP_/REACT_APP_/VITE_/NEXT_PUBLIC_） |
| 组件库 | deps + `src/components` | 是否二开换肤（DOM 前缀≠官方文档） |
| 部署 | CI 文件 / deploy 脚本 / nginx conf | 产物形态、托管方式、回滚 |
| 后端接入 | dev proxy / 网关路由规范 | 前端→网关→服务链路；API 前缀与业务码约定 |

## 通用扫描方法

1. 先读根 `package.json`（框架/包管理器/engines）→ 再读锁文件确认包管理器 → 再读构建配置。
2. 环境变量优先级：`.env.local` > `.env.development` > `.env`；`.env.local` 不入库，需与 `.env.local.example` 对照找键名。
3. proxy 配置从构建工具配置里读（vue.config.js 的 devServer.proxy / vite 的 server.proxy），不靠猜。
4. monorepo：先扫根 workspaces 声明，再逐个进入可运行子包（有 dev/serve/start 脚本的）扫各自信号。
5. 微前端判定：deps 含 `qiankun`/`micro-app` 或存在注册配置 → 走对应子类型 profile。

## 与后端 context 的边界

- 前端画像只写"前端能实证"的项：dev server、模块注册、proxy 目标、路由、构建部署、组件库。
- 后端服务地址/中间件连接（网关内部、DB、MQ）属于 `devlab-context-bootstrap` 五件套职责，前端画像只记录"代理到 X 网关 / 经 Y 前缀"，不展开后端细节。
- 两套产物通过 bootstrap 五件套汇总合并：前端画像的 `dev_proxy` 条目与后端台账的网关条目互为镜像，bootstrap 负责对齐。

## 敏感信息边界（所有子类型通用）

- 密码/令牌/私钥永不写入画像 value；只写环境变量引用（如 `$VUE_APP_API_TOKEN`）或"详见 <config_file>"。
- `.env.local` 中的真实值禁止进入画像；画像只记录键名与用途。
