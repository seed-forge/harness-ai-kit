# Vue Profile（实战级）

> 实证来源：`devlab-web-bootstrap`（v1.0.1 全量迁移）+ `devlab-web-context`
> profiles/vue-microfrontend（实战级信号）。本 profile 覆盖六域完整工作流。

## 适用判定

`package.json` 含 `vue` / `vue-router` / `@vue/cli-service` / `nuxt`，或用户显式指定
`framework=vue`。语言基线默认 TypeScript（`ts`），JS 项目按降级差异执行。

## 六域工作流

### 域 1：Project Bootstrap（初始化工程化）

入口：`workflows/bootstrap.md`（5 阶段：扫描 → 决策卡片 → 生成 → 建议 → 验证）。

脚手架选择（**只引用不重写**）：
- Vue3 + Vite + TS → `npm create vue@latest`（官方 create-vue）
- Vue3 + Vite 无框架模板 → `npm create vite@latest`
- Vue2 + Webpack 存量 → 保留 vue-cli-service（`@vue/cli-service`），按 Webpack 兼容层适配

生成物（`profiles/vue/scripts/*.template` 拷贝到项目 `scripts/`）：

| 文件 | 用途 |
|------|------|
| `common.sh` | 函数库：use_node / check_port / kill_port / write_pid / read_pid / setup_registry / install_deps_incremental |
| `dev.sh` | 开发服务器（start/stop/restart/status/log），框架命令参数化 |
| `build.sh` | 生产构建（多环境 test/prod） |
| `test.sh` | 单元测试 + E2E（自动检测 Jest/Vitest/Cypress） |
| `lint.sh` | ESLint/Prettier/Stylelint |
| `doctor.sh` | 10 项环境诊断（Node 版本/依赖完整性/端口/磁盘/构建产物/registry 连通性等） |
| `orchestrator.sh` | （monorepo 可选）批量启停/健康检查/日志聚合 |
| `.env.local.example` | 环境变量模板（占位符） |

### 域 2：Build（构建）

- 工具链识别：`vite.config.*` → Vite 主线；`vue.config.js` → Webpack（vue-cli）兼容层
- Vite 主线：`vite build --mode production`；Webpack 兼容：`npm run build:prod`
- 多环境：test/simulate/prod → 分支映射（可选）
- 构建验证：dist/ 产物存在性 + 关键文件检查 + 产物大小
- 排障引用：`references/REFERENCE-BUILD-TOOLS.md`（Vite/Webpack 配置要点）、
  `profiles/vue/REFERENCE-PITFALLS.md`

### 域 3：Dependency（依赖治理）

- 包管理器：npm 主线 / pnpm（monorepo 推荐）/ yarn 兼容
- 锁文件强制：package-lock.json / pnpm-lock.yaml / yarn.lock 必须入库
- 增量安装：`install_deps_incremental`（package.json + 锁文件指纹比对）
- 循环依赖检测与公共依赖提升（monorepo）
- 原则：`principles/dependency-governance.md`

### 域 4：Packaging（打包与交付）

- 构建产物：dist/（静态资源 + index.html + 资源哈希）
- 容器化：多阶段 Dockerfile（node:20-alpine build → nginx:alpine serve），
  nginx.conf 需配 SPA history 路由 fallback（`try_files $uri $uri/ /index.html`）
- 微前端交付：base/sub-app 独立构建产物 + 端口协调（见微前端场景层）
- 交付物清单：dist 目录 + 镜像 tag + nginx 配置 + 部署说明

### 域 5：Runtime/Environment（运行环境）

- Node 版本管理：nvm / fnm / volta（`references/REFERENCE-NODE-VERSION-MGT.md`）
- 环境变量：VUE_APP_ / VITE_ 前缀规范；.env.local（个人）+ .env.development（团队共享）
- 端口策略：固定 / 动态分配 / 用户名哈希
- 制品源：私有 registry + 官方源降级（`references/REFERENCE-REGISTRY-STRATEGY.md`）
- API 地址：从 `devlab-infra-usage` 查询推荐值，不硬编码

### 域 6：Engineering Convention（工程规范）

- TypeScript 严格模式（tsconfig strict + vue-tsc 类型检查入 lint）
- ESLint + Prettier + Stylelint（vue3 用 eslint-plugin-vue flat config）
- 项目结构规范：`principles/project-structure.md`（src/ 分层：views/components/composables/stores/services）
- 组件工程边界：组件工程结构（目录/命名/Props 契约）归本技能；
  组件视觉/交互细节归 `devlab-ui-taste-ops`
- 可复现构建：`principles/build-reproducibility.md`

## 微前端场景层（qiankun / micro-app）

> 实证：vue-microfrontend 是本工作区实战形态（devlab-web-context 实战级 profile）。

### 识别信号

- qiankun：`@qiankun/*` 依赖 + 主应用/子应用注册配置
- micro-app：`@micro-zoe/micro-app`

### 关键配置点

1. 主应用端口 / 子应用注册列表（activeRule + entry）
2. 子应用 `base` 配置（`$route.params` 刷新即空 → 必须链式导航进入）
3. 端口协调：多子包固定端口映射（如 21010-21012）
4. 构建产物：子应用独立 dist + 主应用按 entry 加载
5. 公共依赖：react/vue 提升到主应用（避免多实例）

详情见 `profiles/vue/REFERENCE-MICRO-FRONTEND.md`。

## 工具链层（toolchain/）

| 工具链 | 定位 | 参考 |
|--------|------|------|
| Vite | 主线（新项目默认） | `profiles/vue/toolchain/REFERENCE-VITE.md` |
| Webpack / vue-cli | 存量兼容（Vue2 项目） | `profiles/vue/toolchain/REFERENCE-WEBPACK.md` |

## 引用

- `profiles/vue/REFERENCE-PITFALLS.md` — 5 个高频踩坑案例（web-bootstrap 实证迁移）
- `profiles/vue/REFERENCE-VUE.md` — Vue 项目特定配置
- `profiles/vue/REFERENCE-MICRO-FRONTEND.md` — 微前端场景
- `references/REFERENCE-BUILD-TOOLS.md` — 跨框架构建工具
- `references/REFERENCE-MONOREPO.md` — monorepo 管理
