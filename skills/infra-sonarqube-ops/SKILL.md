---
name: infra-sonarqube-ops
description: SonarQube 代码质量平台 day-2 运维：探活、项目管理、质量门禁、扫描触发与结果解读、Token 管理。配套 CLI sonarqubectl。当用户提到 SonarQube、sonarqubectl、代码质量扫描、质量门禁、sonar-scan 时触发。
---

# infra-sonarqube-ops

SonarQube Community Edition 代码质量平台的 day-2 运维操作手册。覆盖健康检查、项目管理、质量门禁配置与查询、扫描任务触发与结果解读、Token 生命周期管理。

## 平台信息

| 项 | 值 |
|----|-----|
| 主机 | <host> (<host>) |
| 版本 | 10.7.0 Community Edition |
| 域名 | sonarqube.{base_domain} |
| 端口 | 19000 |
| 直连 URL | http://sonarqube.{base_domain}:19000 |
| 镜像 | sonarqube:10.7.0-community |
| 部署路径 | 1panel/apps/sonarqube/sonarqube/ |
| 数据存储 | data→/opt/sonarqube/data, extensions→/opt/sonarqube/extensions, logs→/opt/sonarqube/logs |

## 用途

- 平台健康检查与探活
- 项目 CRUD 管理
- 质量门禁列表、详情、项目状态检查
- 扫描任务触发与状态查询
- 项目指标（Bugs/Vulnerabilities/Coverage 等）查看
- 用户 Token 生成/列表/撤销

## 输入

- 项目 Key（project key）
- Token 名称
- 环境变量 `SONARQUBE_URL` + `SONARQUBE_TOKEN`

## 输出

- 健康检查报告（版本、状态）
- 项目列表/详情
- 质量门禁状态（PASSED/ERROR + 条件明细）
- 扫描任务状态（PENDING/IN_PROGRESS/SUCCESS/FAILED）
- 项目指标摘要

## 工作流

### 1. 探活

```bash
# 快速健康检查
sonarqubectl health
# 预期: ✅ SonarQube 10.7.0.96327 — status: UP

# 带 JSON 输出
sonarqubectl --json health
```

### 2. 项目管理

```bash
# 列出所有项目
sonarqubectl project list

# 搜索项目
sonarqubectl project list -q "my-app"

# 查看项目详情
sonarqubectl project get my-project-key

# 创建项目
sonarqubectl project create my-new-project --name "My New Project"

# 删除项目（需确认）
sonarqubectl project delete my-old-project
```

### 3. 质量门禁

```bash
# 列出所有质量门禁
sonarqubectl qualitygate list

# 查看门禁详情（含条件列表）
sonarqubectl qualitygate get 1

# 检查项目的门禁状态
sonarqubectl qualitygate check my-project-key
# 预期输出:
# ✅ Quality Gate: OK
#   new_reliability_rating: A (<= A) → OK
#   new_security_rating: A (<= A) → OK
```

### 4. 扫描任务

```bash
# 查看最近扫描状态
sonarqubectl scan status my-project-key
sonarqubectl scan status my-project-key -n 10  # 最近 10 条

# 触发扫描提示（实际扫描需要 sonar-scanner）
sonarqubectl scan trigger my-project-key
```

### 5. Token 管理

```bash
# 列出当前用户 Token
sonarqubectl token list

# 生成新 Token（输出仅显示一次）
sonarqubectl token create ci-token
# ⚠️ Save this token — it won't be shown again.

# 撤销 Token（需确认）
sonarqubectl token revoke old-token
```

### 6. Jenkins 集成（L3）

Jenkins Shared Library 的 `sonarScan.groovy` 实现完整的 L3 集成：

```groovy
// Jenkinsfile 中调用
sonarScan(
    projectKey: 'my-project',
    serverUrl: env.SONAR_URL,
    token: env.SONAR_TOKEN,
    qualityGate: true,
    qualityGateTimeout: 120
)
```

流程：触发 sonar-scanner → 轮询 CE task 完成 → 查询 quality gate → FAILED 则 `error()` 阻断 → 输出指标摘要。

### 7. Woodpecker 集成

Woodpecker config-extension 的 `sonar.py` 提供完整的多层配置合并 + event/branch 过滤 + step 构建能力。通过环境变量控制：

- `WOODPECKER_SONAR_ENABLED` — 总开关
- `WOODPECKER_SONAR_HOST_URL` — SonarQube 地址
- `WOODPECKER_SONAR_PROJECT_KEY` — 项目 Key
- `WOODPECKER_SONAR_EVENTS` — 触发事件（默认 push）
- `WOODPECKER_SONAR_BRANCHES` — 触发分支（默认 main,master）

## 配置上下文

本技能依赖以下配置，AI 在运行时按如下优先级解析：

1. 用户对话中明确提供的值（最高优先级）
2. `~/.harness-ai-kit/config.yaml` 中 `assets.infra-sonarqube-ops` 或 `global` 段
3. `config.defaults.yaml` 中的默认值

如用户未提供且无默认值的 required 字段，**必须主动询问用户**。
禁止从 AGENTS.md 或脚本中读取硬编码配置值。

## 推荐输出格式

执行完毕后输出极简回执：**状态**（✅ 成功 / ⚠️ 部分成功 / ❌ 失败）+ **关键结果**（1-2 行，如操作对象、产出位置、下一步）。无需强制套用大表格。

## 约束

- **社区版限制**: 不支持分支分析（Branch Analysis）、PR Decoration
- **环境适配**：主机名 <host>/<host> 为逻辑名示例；IP/域名使用占位符（`{hs_host}`/`{base_domain}`/`{root_domain}` 等），解析自 `~/.harness-ai-kit/config.yaml` 顶层字段，规范见 docs/config-governance.md。
- **主干扫描模式**: 所有扫描结果合并到 main 分支视图
- **网络模式**: Docker host network，端口变更需同步改 compose + DDNS + OpenResty
- **认证**: 使用 User Token（非密码），Token 生成后仅显示一次
- 配套 CLI `sonarqubectl` 提供命令行操作入口
- Jenkins 集成通过 `sonarScan.groovy` Shared Library 实现

## CE 与 DE 功能差异

| 功能 | Community Edition | Developer Edition+ |
|------|:--:|:--:|
| 代码扫描 | ✅ | ✅ |
| 质量门禁 | ✅ | ✅ |
| API 完整 | ✅ | ✅ |
| 分支分析 | ❌ | ✅ |
| PR Decoration | ❌ | ✅ |
| 高级规则 | 部分 | ✅ |

## 专题引用

| 文件 | 用途 |
|------|------|
| [REFERENCE-API.md](references/REFERENCE-API.md) | SonarQube Web API 端点参考 |

## 示例

**场景**: 用户说「帮我看看 SonarQube 是否正常，然后检查一下 my-app 的质量门禁」

**合格输出**:
1. `sonarqubectl health` 确认平台在线
2. `sonarqubectl qualitygate check my-app` 查看门禁状态
3. 如果 ERROR，列出失败条件并给出修复建议
4. `sonarqubectl scan status my-app` 查看最近扫描时间

## Human Decisions

> 结构化同源见 `decisions.yaml`；以下为人类可读汇总。

| # | 决策点 | 触发条件 | 选项 | 默认行为 |
|---|--------|---------|------|---------|
| HD-1 | 删除项目 | 准备删除 SonarQube 项目时 | 确认后删除 / 取消 | 必问 |
| HD-2 | 重置 Token | 准备重置/重新生成 Token 时 | 确认后重置 / 取消 | 必问 |

参考文档：
- references/REFERENCE-SONARQUBECTL-CLI.md
