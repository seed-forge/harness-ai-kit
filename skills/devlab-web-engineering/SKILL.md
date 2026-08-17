---
name: devlab-web-engineering
description: Web / 前端工程化能力层（Frontend Engineering Capability）。语言无关覆盖六域：Project Bootstrap、Build、Dependency、Packaging、Runtime/Environment、Engineering Convention。路由键 = 语言 × 框架 双维：TS 主线 / JS 兼容 / 语言维度扩展位 → 框架路由 profiles/vue（实战级：Vite 主线/Webpack 兼容 + 微前端场景层 qiankun/micro-app）、profiles/react（模板级），其余框架走 references 引用层。Capability Layer：原则沉淀 + 能力编排 + Profile + 工程质量要求，不承接完整用户需求，不重复造底层工具。由 devlab-web-bootstrap 吸收升级而来。
---

# devlab-web-engineering

Web / 前端工程化能力层。从工程化六域入手，覆盖项目初始化、构建、依赖、打包与交付、
运行环境与工程规范，按「语言 × 框架」路由到对应 Profile 执行，一站式交付**可构建、
可打包、可部署**的前端项目。

> **Capability Layer 定位**：本技能是能力层，负责工程化原则、能力编排、Profile 与
> 工程质量要求；不承接完整用户需求，不重复造底层工具——优先复用社区 Skill / Reference /
> CLI / MCP 及现有 DevLab Capability（create-vue / create-vite / 框架官方文档等只引用不重写）。
> UI/UX 品味、视觉操作、QA/测试、Contract、CI/CD 等独立领域能力不在此范围（见 Out of Scope 路由表）。

## 触发条件

- 用户说"初始化前端项目工程""配构建配置""帮我打包前端""工程化规范"
- 新项目需要工程化引导（识别语言×框架后路由到对应 profile）
- 现有项目构建/打包/容器化/微前端排障（构建失败、产物异常、镜像路径等）
- 从旧式打包（无锁文件 / CRA）迁移到现代模式（Vite / lockfile / pnpm）
- `devlab-project-bootstrap` Phase 4 编排路由（前端项目工程化初始化）

## 输入参数

| 参数 | 必填 | 说明 | 示例 |
|------|------|------|------|
| `workspace` | 否 | 项目工作目录（默认当前目录） | `/workspace/my-web` |
| `framework` | 否 | 框架显式指定（默认自动识别） | `vue` / `react` |
| `workflow` | 否 | 只跑指定流程（默认全流程） | `bootstrap` / `build` / `packaging` |

## 语言 × 框架识别路由

路由键 = **语言 × 框架** 双维。先识别语言（决定工程基线），再识别框架（决定加载哪个 Profile）。

### 语言维度

| 语言 | 处理 |
|------|------|
| TypeScript（主线） | 默认基线，所有 profile 按 TS 工程标准（tsconfig 严格模式、类型检查入 lint） |
| JavaScript（兼容） | profile 内降级差异：JSDoc 替代类型、跳过 tsc 类型检查 |
| 其他（扩展位） | references 层预留说明；WASM 等后续版本再建 profile |

### 框架维度（识别信号）

| 识别信号 | 框架 | Profile |
|---------|------|---------|
| `package.json` 含 `vue` / `vue-router` / `@vue/cli-service` / `nuxt` | vue | `profiles/vue.md` |
| `package.json` 含 `react` / `react-dom` / `next` | react | `profiles/react.md` |
| `package.json` 含 `@angular/core` / `angular.json` | angular | references 引用层 |
| 多种并存 / 识别不到 | — | 进 Phase 0 D0 卡片让用户确认 |

构建工具（Vite 主线 / Webpack 兼容 / Next.js 等）在 profile 内 toolchain 层识别，不作为路由键。

## 工作流

```
Phase 0: 决策确认（内建）  ← 关键分歧在此收敛（语言×框架/包管理器×工具链/端口/运行时/制品源/环境变量/编排）
    ↓ decisions
Phase 1: 工程化基线分析（内建）→ project_profile（框架、构建工具、依赖、容器现状）
    ↓ project_profile
Phase 2: 按路由键分发
    ├─ vue   → profiles/vue.md（实战级：六域完整工作流 + 微前端场景层）
    └─ react → profiles/react.md（模板级）
    ↓ 各 profile 执行 bootstrap / build / packaging 对应 workflow
Phase 3: 验证闭环（内建）→ verification_report（脚本验证 + 构建验证 + 启动探测）
```

> **核心原则**：Phase 0 收敛所有工程决策后再动手修改。禁止在决策未确认的情况下
> 直接修改 package.json / vite.config.* 等工程文件。

### Phase 0: 决策确认

**目标**：在进入任何配置修改之前，把关键分歧点一次性摆到用户面前，让用户拍板。

#### 0.1 快速扫描（自动）

```
0. 识别语言与框架（最先做，见路由表）
1. 检测 package.json 是否存在 → 不存在则标记为「从零创建」
2. 扫描现有 scripts / 构建配置（vite.config.* / webpack.config.* / next.config.*）→ 判断当前构建模式
3. 扫描依赖目录（node_modules/）与锁文件（package-lock.json / pnpm-lock.yaml / yarn.lock）
4. 扫描仓库配置（.npmrc / .yarnrc）→ 是否已指向私有 registry
5. 扫描 Dockerfile / nginx.conf / docker-compose.yml → 判断交付方式
6. 探测运行时（顺序）：
   a. PATH 中的 node
   b. 回退常见版本管理器路径（nvm / fnm / volta）
   c. 都没有 → 标记缺失，进 D3 提示安装
7. 探测包管理器（npm / pnpm / yarn）与构建工具可执行性，缺失只告警不阻断
```

#### 0.2 决策卡片（展示给用户确认）

```markdown
## 📋 前端工程化决策确认

### 自动检测结果
| # | 检测项 | 结果 | 来源 |
|---|--------|------|------|
| 0 | 语言/框架 | {ts/vue / ts/react / js/vue ...} | package.json |
| 1 | 构建工具 | {vite / webpack / next / 未检测到} | 构建配置文件 |
| 2 | 包管理器 | {npm / pnpm / yarn} | packageManager + 锁文件 |
| 3 | 运行时版本 | {18 / 20 / 22} | .nvmrc / engines / 探测 |
| 4 | 制品源 | {私有 registry / 官方源} | .npmrc |
| 5 | 已有脚本 | {N 个 / 无} | scripts/ 目录 |
| 6 | 容器化交付 | {有 Dockerfile / 无 / 有 nginx.conf} | 文件系统扫描 |

### 需要你确认的决策

**D0. 语言×框架确认**（仅在识别不到或多种并存时询问）
  识别结果: {ts/vue / ts/react / 未识别}
  → 确认: ____

**D1. 包管理器×工具链选择**
  - 包管理器: npm（主线）/ pnpm（推荐 monorepo）/ yarn
  - 构建工具: Vite（主线）/ Webpack（存量兼容）
  → 你的选择: ____

**D2. 端口策略**（多开发者环境）
  A. 固定端口（单开发者）[推荐]
  B. 动态分配（多开发者）
  C. 用户名哈希（避免冲突）
  → 你的选择: ____

**D3. 运行时版本确认**（探测结果确认或修正）
  → 确认: ____

**D4. 制品源 registry 策略**
  A. 私有源 + 官方源降级 [推荐]
  B. 仅官方源
  → 你的选择: ____

**D5. API 地址**（默认从 基础设施配置源(registry/API 地址) 读推荐值，非必问）
  → 确认: ____

**D6. 环境变量规范**
  A. .env.local（个人）+ .env.development（团队共享）[推荐]
  B. 只用 .env.local
  → 你的选择: ____

**D7. monorepo 编排 + 已有脚本冲突**（检测到时询问）
  - 生成 orchestrator.sh: [是/否]
  - 已有脚本处理: [保留并新目录 / 覆盖 / 合并函数 / 跳过]
  → 你的选择: ____
```

#### 0.3 决策锁定

用户确认后，将决策固化为 `decisions` 对象，后续所有 Phase 以此为准（示例）：

```yaml
decisions:
  language: ts              # D0: ts | js
  framework: vue            # D0: vue | react
  build_tool: vite          # D1
  package_manager: pnpm     # D1
  port_strategy: fixed      # D2
  runtime_version: "20"     # D3
  registry_strategy: fallback  # D4
  env_var_spec: layered     # D6
  orchestrator: true        # D7
  existing_scripts: merge   # D7
```

> **约束**：`language × framework` 决定 Phase 2 加载哪个 profile；具体工具链逻辑
> 下沉到 profile 的 toolchain/reference，主体只做识别与路由。

## Out of Scope 路由表

| 需求 | 路由到 |
|------|--------|
| UI/UX 品味、视觉精修、Design System | `devlab-ui-taste-ops` |
| 浏览器操作/截图/视觉回归/视觉走查 | `devlab-web-visual-ops` |
| QA 验收、质量门禁、上线前检查 | `devlab-qa-ops` |
| 测试体系搭建 / E2E 用例 | `devlab-test-onboard` / `devlab-web-test-e2e` |
| Web↔Server 契约（接口/序列化一致性） | `devlab-contract-web-server` |
| CI/CD 管线编排 | `你的 CI/CD 接入流程` |
| 浏览器扩展（WebExtension/MV3） | `devlab-web-extension-bootstrap` |
| State Management 方案选型（业务架构决策） | 业务架构/领域设计（暂无专有资产，不建实体） |
| 基础设施信息查询（Nexus/registry/API 地址） | `基础设施配置源(registry/API 地址)` |

## Integration Points

| 目标资产 | 类型 | 方向 | 契约（输入→输出） |
|---------|------|------|-----------------|
| `基础设施配置源(registry/API 地址)` | skill | outbound | 查询 registry 地址/凭据/API 推荐值 → 仓库与环境配置 |
| `devlab-web-context` | skill | inbound/outbound | 模式A：被委托按 profiles/ 规则扫描 → 画像；工程化改动前消费 context 画像 |
| `你的 CI/CD 接入流程` | skill | outbound | 构建配置完成后 → CI/CD 管线接入 |
| `devlab-project-bootstrap` | skill | inbound | Phase 4 编排路由 → 本技能执行前端工程化初始化 |
| `devlab-qa-ops` | skill | outbound | 工程化交付后 QA 验收（横向 web/srv） |
| `devlab-ui-taste-ops` | skill | outbound | UI 精修/设计边界（组件工程结构归本技能，视觉/交互归 ui-taste-ops） |
| `devlab-web-extension-bootstrap` | skill | outbound | 浏览器扩展场景路由 |

## 约束

- **Phase 0 决策优先**：所有工程配置修改必须基于 Phase 0 用户确认的 `decisions`，禁止跳过。
- **路由键不绑死**：语言×框架识别与工具链具体逻辑一律下沉到 `profiles/{framework}.md` 及
  其 toolchain/reference，主体只做识别与路由；新增框架按 `profiles/` 目录骨架扩展。
- **不重复造轮子**：社区成熟方案（create-vue / create-vite / 框架官方脚手架）优先引用，
  不重新实现底层工具。
- **不自动修改业务代码**：只生成/修改工程配置文件与脚本，不改 src/ 目录业务代码。
- **不覆盖已有脚本**：检测到同名文件时提示用户选择。
- **不包含私有信息**：生成的 .env.local.example 只有占位符；registry/API 地址从
  基础设施配置源(registry/API 地址) 获取，不硬编码。
- **增量生成**：已有部分脚本时只补充缺失的。
- **Bash 兼容性**：要求 Bash 4.0+，兼容 Linux/macOS。
- **交互限制**：最多 8 个决策点（D0-D7），不确定时用合理默认值。
- **验证强制**：所有生成的 .sh 必须通过 `bash -n` 和 shellcheck。
- 不自动执行 `npm publish` / 部署命令，仅生成命令供用户确认。

## 配置上下文

本技能运行时配置通过 `基础设施配置源(registry/API 地址)` 技能获取，包括：
- 私有 npm registry 地址与凭据（.npmrc 配置模板）
- 推荐 API 地址（基础设施配置源(registry/API 地址) 查询）
- 部署目标信息

配置优先级：`基础设施配置源(registry/API 地址)` 查询结果 > 项目已有配置 > 本技能默认值。

## 专题引用

### 框架 Profile（Phase 2 按框架加载）

- Vue（实战级，含 Vite 主线/Webpack 兼容 toolchain + 微前端场景层）：
  [profiles/vue.md](profiles/vue.md)
- React（模板级）：[profiles/react.md](profiles/react.md)

### 流程（workflows/）

- [bootstrap](workflows/bootstrap.md)：项目初始化工程化流程
- [build](workflows/build.md)：构建流程
- [packaging](workflows/packaging.md)：打包与交付流程（容器化/静态部署/微前端）

### 原则（principles/）

- [构建可复现性](principles/build-reproducibility.md)
- [依赖治理](principles/dependency-governance.md)
- [项目结构](principles/project-structure.md)
- [环境一致性](principles/environment-consistency.md)

### 知识库（references/）

- [索引](references/REFERENCE-INDEX.md)
- [社区引用清单](references/community/COMMUNITY-REFERENCES.md)
- [构建工具配置（跨框架）](references/REFERENCE-BUILD-TOOLS.md)
- [Monorepo 管理](references/REFERENCE-MONOREPO.md)
- [Node 版本管理](references/REFERENCE-NODE-VERSION-MGT.md)
- [Registry 策略](references/REFERENCE-REGISTRY-STRATEGY.md)

### 库使用指南（usage 家族）

- [ECharts 集成](devlab-web-echarts-usage)：tree-shaking、IntersectionObserver 按需加载、Astro Islands 数据传递
- [@xyflow/react](devlab-web-xyflow-usage)：核心概念、自定义节点、Astro Islands 集成、踩坑经验

## 示例

### 示例 1：新 Vue3 + Vite 项目工程化初始化（完整流程）

用户说："帮我初始化一个 Vue3 + Vite + TS 的前端工程，生成开发脚本。"

```
Phase 0: 识别 ts/vue → 输出决策卡片
  → D1=Vite+pnpm, D2=固定端口, D3=Node 20, D4=私有源降级, D5=API 默认值, D6=分层 .env
Phase 1: 扫描项目结构 → project_profile
Phase 2: 路由 profiles/vue.md → 六域配置（tsconfig/ESLint/Prettier/依赖/脚本）
Phase 3: 生成 scripts/*（dev/build/test/lint/doctor）→ bash -n + shellcheck → 验证报告
```

### 示例 2：存量 Vue 微前端项目构建排障

用户说："微前端子应用构建后主应用加载不到。"

```
Phase 0: 识别 vue + qiankun → 决策卡片
Phase 2: 路由 profiles/vue.md 微前端场景层 → 检查 base 配置/子应用注册/端口协调
Phase 3: 构建验证 → 输出报告
```

### 示例 3：React 项目迁移到 Vite

用户说："把 CRA 项目迁移到 Vite。"

```
Phase 0: 识别 react + CRA → 决策卡片（迁移确认）
Phase 2: 路由 profiles/react.md → vite 迁移 checklist（react-scripts → vite）
Phase 3: 构建验证 → 输出报告
```

## Human Decisions

> 结构化同源见 `decisions.yaml`；以下为人类可读汇总。

| # | 决策点 | 触发条件 | 选项 | 默认行为 |
|---|--------|---------|------|---------|
| HD-1 | 工程配置修改确认（改造前） | Phase 0 分析现有工程配置后、修改 package.json/构建配置之前 | 用户确认架构判断后再改造 / 补充分析 | 必问 |
| HD-2 | 工具版本卡片选择确认 | 展示 Node 多版本工具卡片、需选定版本时 | 用户确认版本选择 / 采用推荐默认 | 必问 |
| HD-3 | 已有脚本冲突处理 | D7 检测到已有 scripts 时 | 覆盖 / 合并 / 跳过 | 必问 |
