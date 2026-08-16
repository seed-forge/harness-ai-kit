---
name: devlab-test-onboard
description: AI 驱动的分层测试体系顶层路由编排。根据项目特征（前端/后端/全栈/微服务）智能识别测试需求，路由到对应子技能（devlab-web-test-e2e / devlab-srv-test-api / devlab-integration-fullstack）。
---

# AI 驱动的分层测试体系 — 智能编排与路由

**这是企业级测试技能体系的顶层编排入口。**

根据项目特征自动识别测试需求类型，智能路由到对应的子技能执行。支持前端 E2E、后端 API、全栈集成等多种场景。

**核心职责**：
- ✅ 项目测试场景智能识别
- ✅ 子技能推荐与编排
- ✅ 测试数据服务依赖诊断
- ✅ 专家知识库关联检索

---

## 触发条件

当用户提到以下关键词时触发此 Skill：
- "初始化测试" / "test onboarding"
- "配置自动化测试" / "setup test suite"
- "新项目接入测试" / "project test integration"
- "Playwright/Vitest/API 测试" 

---

## 场景识别矩阵

收到任务后，首先识别项目特征并路由到对应子技能：

| 项目特征 | 检测依据 | 推荐子技能 | 辅助资产 |
|---------|---------|-----------|---------|
| **Vue/React 前端** | `vite.config.ts`, `package.json`(react/vue) | `devlab-web-test-e2e` | `@playwright/test` |
| **纯 API 后端** | `openapi.yaml`, `swagger.json`, `k8s/` | `devlab-srv-test-api` | `supertest`, `jest` |
| **全栈应用** | 同时有前端 + 后端特征 | `devlab-integration-fullstack` | `@playwright/test` + `supertest` |
| **单体后端** | `pom.xml`(java), `requirements.txt`(python) | `devlab-srv-test-api` | `pytest`, `jest` |
| **微服务集群** | `docker-compose.yml`(多服务) | `devlab-integration-fullstack` | `testcontainers`, `mock-server` |
| **性能/容量需求** | 用户提“压测/性能测试/容量验证/性能门禁”；仓库有 `tests/perf/` 或 `.jmx` | `devlab-app-test-perf` | `grafana/k6`（代码化）/ MeterSphere（平台化）|

注：性能测试与上方四类**正交**——功能测试答“对不对”，性能测试答“够不够快/撑不撑得住”，可与任一功能档并行接入。

---

## 执行流程图

```
用户请求 → 扫描项目特征 → 场景识别 → 子技能路由 → 安装建议 → 用户确认 → 执行初始化
    ↓                              ↓            ↓
   触发词匹配                  Vue/React/API/Fullstack    devlab-test-onboard
```

---

## 子技能说明

### 1. `devlab-web-test-e2e` (Web E2E 测试)

**职责**：专门处理浏览器端端到端测试能力。

**功能范围**：
- Playwright 测试代码生成
- Vue/React 组件交互测试
- 视觉回归测试
- 前端性能指标采集
- Flaky test 检测与治理

**推荐 CLI**：
```bash
npm install -D @playwright/test vitest
npx playwright init-agents --loop=claude
```

**参考文档**：
- [Vue Playwright 模板](./references/vue-playwright-seed.md)
- [Healer Classifier](./references/healer-classifier.md)

---

### 2. `devlab-srv-test-api` (Service API 测试)

**职责**：专门处理后端 API 接口测试能力。

**功能范围**：
- OpenAPI/Swagger 文档解析
- REST/GraphQL 接口自动化测试
- 身份认证/授权验证
- 数据一致性校验
- 微服务链路追踪测试

**推荐 CLI**：
```bash
npm install -D jest supertest supertest-fetch
```

**参考文档**：
- [API Analysis Patterns](./references/api-analysis.md)
- [Auth Testing Strategies](./references/auth-testing-patterns.md)

---

### 3. `devlab-integration-fullstack` (全栈集成测试)

**职责**：处理跨前端后端的复杂业务流程测试。

**功能范围**：
- 端到端业务流程验证
- 消息队列集成测试
- 分布式事务补偿验证
- 跨服务数据流追踪
- 事件驱动架构测试

**推荐 CLI**：
```bash
npm install -D @playwright/test testcontainers supertest
```

**参考文档**：
- [E2E Business Flow Patterns](./references/e2e-busines-flow.md)
- [Database Transaction Compensation](./references/db-transaction-compensation.md)

---

### 4. `devlab-app-test-perf` (应用级性能测试)

**职责**：处理性能/容量类验证，与上三类功能测试正交。

**功能范围**：
- k6（代码化）vs MeterSphere（平台化）选型决策
- 阈值即代码的压测脚本编写（thresholds 驱动 CI 红/绿）
- 指标经 Prometheus Remote Write 入 远程时序库，Grafana 看板按 testid 过滤
- CI 性能门禁接入（编排归 `devlab-cicd-onboard` 的 quality-gate 环节）
- 集群服务容量基线巡检

**推荐 CLI**：
```bash
pip install prometheusctl        # 写入面 fail-fast 验证
docker pull grafana/k6:0.54.0   # 固定版本，禁用 latest
```

**参考资产**：
- `server-apps/perf-tests/`（run-k6.sh 包装器 + 巡检场景 + CI step 模板）
- 委派：`infra-observability-ops`（看板/平台）、`infra-metersphere-ops`（平台化压测）

---

## 共享资源（自动引用）

所有子技能都会自动引用以下共享资源：

### 🔧 Fixture Libraries（固定库）
- 测试数据工厂模板
- 通用 Fixtures 定义
- API 请求助手函数

### 📚 Expert Knowledge Base
- 最佳实践指南
- 反模式预警
- 故障排除手册

---

## Bootstrap 集成方式

当用户使用 `devlab-project-bootstrap` 时，会在 **Phase 3.5 测试体系建议阶段**自动调用本技能：

```javascript
// Phase 3.5: 测试体系建议
function detectTestScenario(workspace) {
  const features = scanProject(workspace);
  
  if (features.has('vue') || features.has('react')) {
    recommend([
      skills: ['devlab-web-test-e2e'],
      cli: ['@playwright/test'],
      auto_reference: ['devlab-test-expert']
    ]);
  } else if (features.has('openapi')) {
    recommend([
      skills: ['devlab-srv-test-api'],
      cli: ['supertest', 'jest']
    ]);
  } else if (features.has('fullstack')) {
    recommend([
      skills: ['devlab-integration-fullstack'],
      cli: ['@playwright/test', 'testcontainers']
    ]);
  }
}
```

**用户确认后自动执行**：
1. npm/yarn 安装指定 CLI 包
2. npx 运行初始化命令（如 `playwright init-agents`）
3. 生成基础测试文件模板
4. 配置 AGENTS.md 中测试相关章节

---

## 已知限制

- ❌ **不包含**：单元测试框架的详细配置（由被调用的子技能负责）
- ❌ **不包含**：持续集成流水线的具体编写（由 CI/CD 相关技能负责）
- ⚠️ **依赖诊断**：会自动提示测试数据服务的安装建议，但不直接部署

---

## 扩展阅读

- [测试分层架构设计](./references/test-layer-architecture.md)
- [企业测试数据实践调研](https://example.com/test-data-practices)
- [Playwright 官方文档](https://playwright.dev/docs/intro)
- [TestContainers 最佳实践](https://www.testcontainers.org/)

---

<!-- TRELLIS:START -->
Managed by Trellis. This skill follows the `harness-ai-kit` asset pattern as a routing layer for testing sub-skills.
Last updated: 2026-07-22
Author: AI-assisted architecture refactor based on user consultation.
<!-- TRELLIS:END -->

## Human Decisions

> 结构化同源见 `decisions.yaml`；以下为人类可读汇总。

| # | 决策点 | 触发条件 | 选项 | 默认行为 |
|---|--------|---------|------|---------|
| HD-1 | 测试框架初始化执行 | 扫描项目、识别技术栈、给出安装建议后、执行初始化之前 | 用户确认后执行初始化 / 退回调整建议 | 必问 |
