# Bootstrap 工作流（项目初始化工程化）

> 吸收自 `devlab-web-bootstrap` 5 阶段工作流（扫描 → 交互 → 生成 → 建议 → 验证），
> 按 Phase 0-3 骨架重组。适用于新建前端项目或存量项目补全工程化。

## Phase 1: 扫描项目特征（自动）

```
1. 识别包管理器
   - package.json 的 packageManager 字段（如 "yarn@1.22.11"）
   - 锁文件存在性：yarn.lock / package-lock.json / pnpm-lock.yaml
   - 推荐优先级：显式声明 > 锁文件检测 > 用户选择

2. 识别项目结构
   - Monorepo：检测 workspaces / lerna.json / pnpm-workspace.yaml
   - 单仓库：只有根 package.json
   - 子包类型：app（可运行，有 serve/dev/start 脚本）vs lib（不可运行）

3. 识别构建工具
   - Webpack：vue-cli-service / @vue/cli-service / webpack-dev-server / react-scripts
   - Vite：vite / @vitejs/plugin-*
   - Next.js：next / next dev
   - 从 devDependencies 中提取，用于生成对应启动命令

4. 识别已有脚本
   - 检查 scripts/ 目录下 *.sh 文件
   - 提取关键函数签名（如 use_node / check_port）
   - 检测风格（严格模式 / 日志格式）用于合并时保持一致性

5. 识别环境配置
   - 扫描 .env* 文件：.env / .env.local / .env.development / .env.production
   - 提取端口、API 地址、debug 开关等关键变量
   - 识别框架特定前缀（VUE_APP_ / REACT_APP_ / VITE_ / NEXT_PUBLIC_）

6. 识别微前端架构
   - qiankun：检测 @qiankun/* 依赖 + 主应用/子应用标识
   - micro-app：检测 @micro-zoe/micro-app
   - 提取主应用端口、子应用注册列表
```

## Phase 2: 决策确认（≤8 个问题）

一次性展示 D0-D7 决策卡片（见 SKILL.md Phase 0.2），每个问题提供**推荐值**（来源标注）：

```
D0: 语言×框架确认（识别不到/多种并存时才问）
D1: 包管理器×工具链    推荐: pnpm + Vite（monorepo）或 npm + Vite（单仓）
D2: 端口分配策略        推荐: 固定端口（单开发者）[21010]
D3: Node 版本管理       推荐: nvm（检测到 ~/.nvm 存在）/ fnm / volta / 系统默认
D4: Registry 配置       推荐: 私有源 + 官方源降级
D5: API 服务地址        推荐: devlab-infra-usage 查询值（非必问）
D6: 环境变量规范        推荐: .env.local（个人）+ .env.development（团队共享）
D7: monorepo 编排 + 已有脚本处理  推荐: 生成 orchestrator.sh + 保留并新目录
```

**推荐值来源标注**：`(扫描结果)` 代码/配置文件自动读取；`(devlab-infra-usage)` 基础设施查询；
`(框架约定)` 技术栈最佳实践。

## Phase 3: 生成脚本（基于模板 + 参数化）

从 `profiles/vue/scripts/*.template`（或复用跨框架模板）生成到项目 `scripts/`：

```
3.1 common.sh
    - use_node(): nvm → fnm → volta → 系统 Node 降级
    - allocate_port(): 固定 / 动态分配 / 用户名哈希（21000 + uid % 1000）
    - setup_registry(): 私有源失败自动降级官方源
    - 通用函数：check_port / kill_port / wait_for_port / is_running /
      write_pid / read_pid / install_deps_incremental / 彩色日志

3.2 dev.sh
    - 子命令路由（start/stop/restart/status/log/clean/reset/help）
    - start: use_node → PID 文件防重复 → check_port 清理 → 构建启动命令
      （Vite: vite --port $PORT --host；Webpack: vue-cli-service serve；Next: next dev -p）
    - nohup 后台启动 + PID 写入 + wait_for_port 就绪 + 输出访问地址（本地+局域网）
    - stop: SIGTERM → 等 10s → SIGKILL

3.3 build.sh
    - 多环境支持（test/simulate/prod）+ 环境→分支映射（可选）
    - 构建命令参数化（vite build --mode production / npm run build:prod / next build）
    - 构建验证：dist/ 目录大小 + 关键文件存在性
    - 构建产物打包（可选 .tar.gz）

3.4 test.sh / lint.sh
    - test.sh 自动检测：Jest / Vitest / Cypress
    - lint.sh 自动检测：ESLint / Prettier / Stylelint

3.5 doctor.sh（10 项检查）
    Node 版本 / 包管理器版本 / 依赖完整性 / Git 状态 / 磁盘空间 / 端口可用性 /
    环境配置文件 / 构建产物 / Registry 连通性 / node_modules 缓存异常

3.6 .env.local.example（占位符模板）
    - 框架特定前缀（VUE_APP_ / REACT_APP_ / VITE_ / NEXT_PUBLIC_）
    - 注释说明每个变量的用途

3.7 orchestrator.sh（monorepo 可选）
    - 自动发现所有 app 类型子包；批量启动（并行+健康检查）/ 批量停止（逆序）/
      日志聚合 / 依赖拓扑排序（共享包构建优先）
```

**技术栈特定逻辑注入**：从 `profiles/vue/REFERENCE-VUE.md`、
`profiles/react/REFERENCE-REACT.md`、`references/REFERENCE-BUILD-TOOLS.md`、
`references/REFERENCE-MONOREPO.md` 读取。

## Phase 4: 输出建议（不改代码）

```
4.1 Workspace 依赖优化（monorepo）
    - 识别循环依赖（A → B → A）；建议提升公共依赖到根 package.json
4.2 .env 规范建议
    - 检测 .env.local 是否已纳入 .gitignore；敏感信息泄漏风险；前缀规范
4.3 端口分配建议（多子包）
    - 为每个子包分配固定端口，输出端口映射表
4.4 构建顺序优化（monorepo）
    - 分析依赖拓扑，输出推荐构建顺序
4.5 缓存清理建议
    - 检测 node_modules/.cache 大小异常（> 500MB）
```

## Phase 5: 验证（并入 Phase 3 验证闭环）

```
5.1 bash -n scripts/*.sh（语法检查）
5.2 shellcheck -x scripts/*.sh（忽略 SC1090/SC2312 误报）
5.3 Dry-run：source common.sh 验证函数加载与命令构建，不实际启动服务
5.4 输出验证报告（✅/⚠️/❌ 逐文件）
5.5 生成 scripts/verify.sh 供用户随时复查
```

## 约束

- 不自动修改业务代码（src/ 不动）；不覆盖已有脚本（提示用户选择）
- 增量生成：已有部分脚本时只补充缺失的
- 不包含私有信息：.env.local.example 只有占位符
- 最多 8 个决策点，不确定时用合理默认值
