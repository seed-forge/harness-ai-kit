---
name: devlab-test-expert
description: 测试专家知识库。包含测试最佳实践、故障排查指南、测试策略设计、性能优化建议等专家级知识，供其他测试技能引用。
---

# AI 驱动测试 - 最佳实践专家知识库

**这是企业级测试团队的共享知识中枢。**

聚合最佳实践、反模式预警、故障排除手册等专家知识，供所有测试子技能调用。

---

## 触发条件

当用户提到以下关键词时触发此 Skill：
- "测试最佳实践" / "testing best practices"
- "常见陷阱" / "antipatterns"
- "验收标准怎么写" / "acceptance criteria examples"
- "性能测试怎么做" / "performance testing guide"
- "Flaky test 治理" / "flaky test tactics"

---

## 知识领域索引

### 📚 测试方法论

| Reference | 主题 | 适用场景 |
|-----------|------|---------|
| [testing-maturity-model](references/testing-maturity-model.md) | 测试能力成熟度模型 | 组织评估 |
| [shift-left-testing-strategies](references/shift-left-testing.md) | 左移测试策略 | 流程改进 |
| [test-data-management-best-practices](references/test-data-management.md) | 测试数据管理 | 数据准备 |
| [test-automation-pyramid](references/automation-pyramid.md) | 自动化测试金字塔 | 架构设计 |
| [property-based-testing](references/REFERENCE-PROPERTY-BASED-TESTING.md) | 属性测试模式（fast-check / Hypothesis / jqwik） | 随机数据、性质验证、最小反例 |

### 🎯 前端专项

| Reference | 主题 | 适用场景 |
|-----------|------|---------|
| [ui-selection-stability](references/ui-selection-stability.md) | 选择器稳定性指南 | Web E2E |
| [component-testing-patterns](references/component-testing-patterns.md) | 组件测试模式 | Vue/React |
| [visual-regression-guide](references/visual-regression-guide.md) | 视觉回归测试 | UI 变更 |
| [a11y-testing-checklist](references/a11y-testing-checklist.md) | 可访问性测试清单 | WCAG 合规 |

### 🔧 后端/API 专项

| Reference | 主题 | 适用场景 |
|-----------|------|---------|
| [api-testing-complete-guide](references/api-testing-complete-guide.md) | API 测试完整指南 | REST/GraphQL |
| [authn-authz-testing](references/authn-authz-testing.md) | 身份认证授权测试 | 安全测试 |
| [schema-validation-patterns](references/schema-validation.md) | Schema 验证模式 | OpenAPI |
| [rate-limiting-tests](references/rate-limiting-tests.md) | 限流降级测试 | 高可用 |

### 🛡️ 运维与质量

| Reference | 主题 | 适用场景 |
|-----------|------|---------|
| [flaky-test-detection](references/flaky-test-detection.md) | Flaky Test 检测与治理 | CI/CD |
| [test-performance-benchmarking](references/test-performance-benchmarking.md) | 测试性能基准 | 性能工程 |
| [code-coverage-deep-dive](references/code-coverage-analysis.md) | 代码覆盖率深度分析 | 质量门禁 |
| [security-testing-integration](references/security-testing-integration.md) | 安全测试集成 | AppSec |

### 🔄 持续集成

| Reference | 主题 | 适用场景 |
|-----------|------|---------|
| [ci-cd-integration-guide](references/ci-cd-integration.md) | CI/CD 集成指南 | Jenkins/GitHub Actions |
| [parallel-execution-strategies](references/parallel-execution.md) | 并行执行策略 | Speedup |
| [test-result-analytics](references/test-analytics.md) | 测试结果分析 | Metrics |
| [deployment-gates](references/deployment-gates.md) | 部署门禁配置 | Quality Gates |

---

## 核心知识卡片示例

### Card #1: 测试数据管理最佳实践

**来源**: Enterprise Test Data Research (调研自 Netflix, Spotify, Airbnb)

#### 核心决策树

```javascript
// Step 1: 评估项目复杂度
const complexity = assessProjectComplexity();

// Step 2: 选择测试数据策略
if (complexity === 'SIMPLE') {
  return {
    strategy: 'IN_MEMORY',
    tools: ['Faker.js', 'Factory Girl'],
    maintenance: 'Low',
    isolation: 'Medium'
  };
} else if (complexity === 'COMPLEX') {
  return {
    strategy: 'TEST_CONTAINERS',
    tools: ['Testcontainers', 'LocalStack'],
    maintenance: 'High',
    isolation: 'High'
  };
} else if (complexity === 'DISTRIBUTED') {
  return {
    strategy: 'DEDICATED_TEST_DB',
    tools: ['Postgres with schemas', 'MySQL with databases'],
    maintenance: 'Very High',
    isolation: 'Maximum'
  };
}
```

#### 三种主流方案对比

| 方案 | 优势 | 劣势 | 适用场景 | 复杂度 |
|------|------|------|---------|--------|
| **在内存生成** | 速度快、无外部依赖 | 无法验证真实约束 | 单元测试、简单业务 | ⭐⭐ |
| **Testcontainers** | 真实环境、自动清理 | 启动慢（~5s） | 集成测试、复杂查询 | ⭐⭐⭐⭐ |
| **专用数据库** | 完全隔离、支持大数据 | 运维成本高 | 分布式系统、并发测试 | ⭐⭐⭐⭐⭐ |

#### 实施建议

**推荐组合（渐进式升级）**:

```yaml
Phase 1: 单元测试
  fixtures: faker + factory functions
  scope: business logic validation

Phase 2: 集成测试  
  fixtures: @playwright/test + testcontainers
  scope: database operations

Phase 3: E2E 测试
  fixtures: seed data via API
  scope: cross-service workflows
```

#### 反模式预警

❌ **不推荐做法**:
- 使用生产数据库副本（数据污染风险）
- 硬编码测试数据（维护成本爆炸）
- 依赖全局状态（Flaky Test 根源）

✅ **推荐做法**:
- 每个测试独立 Fixture
- 使用 Factory Pattern 生成数据
- 通过 API 创建而非直接 UI 操作
- 测试后自动清理（before/after hooks）

---

### Card #2: UI 选择器稳定性指南

**来源**: Google Testing Best Practices

#### 选择器优先级矩阵

| 优先级 | 选择器类型 | 稳定性 | 可读性 | 推荐使用 |
|-------|-----------|--------|--------|---------|
| **⭐ P0** | `getByRole('button', { name: 'Submit' })` | 极高 | 优秀 | ✅ 首选 |
| **⭐ P0** | `getByLabel('Email')` | 极高 | 优秀 | ✅ 首选 |
| **⭐ P1** | `getByText(/login/i)` | 高 | 良好 | ✅ 推荐 |
| **⭐ P1** | `getByPlaceholder('Enter email')` | 高 | 一般 | ⚠️ 慎用 |
| **⭐ P2** | `[data-testid="submit-btn"]` | 中 | 需约定 | ⚠️ 需规范 |
| **⭐ P3** | `.btn.primary.submit` | 低 | 差 | ❌ 禁用 |
| **⭐ P4** | `#app > div > button:nth-child(2)` | 极低 | 极差 | ❌ 绝对禁止 |

#### 实战示例

```typescript
// ❌ ANTI-PATTERN: Fragile CSS selector
await page.click('.card-container .item-list li:last-child button');

// ✅ RECOMMENDED: Semantic role-based selector
await page.getByRole('button', { name: 'Delete item' }).click();

// ✅ ACCEPTABLE: Test ID with clear convention
await page.getByTestId('delete-item-button').click();
```

#### ARIA Role 参考表

| 元素 | 正确 Role | 错误 Role |
|------|----------|----------|
| `<button>` | `role='button'` | `role='link'` |
| `<input type="email">` | `role='textbox', aria-label='Email'` | `role='input'` |
| `<nav>` | `role='navigation'` | `role='menu'` |
| Modal Dialog | `role='dialog'` | `role='popup'` |

---

### Card #3: Flaky Test 治理全攻略

**来源**: Netflix Chaos Engineering Principles

#### Flaky Test 分类矩阵

| 类型 | 特征 | 根本原因 | 修复策略 | 优先级 |
|------|------|---------|---------|--------|
| **Race Condition** | 随机失败 | 异步时序问题 | 显式等待 | P0 |
| **Resource Contention** | CI 环境频发 | 资源竞争 | 增加超时/隔离 | P1 |
| **External Dependency** | 第三方服务不稳定 | 网络延迟 | Mock Server | P0 |
| **Data Pollution** | 测试顺序相关 | 全局状态 | 测试隔离 | P1 |
| **Browser Rendering** | 特定浏览器 | DOM 渲染延迟 | 增加 waits | P2 |

#### 诊断流程图

```
测试失败 → 查看 Trace 文件
         ↓
      是否有 Timeout?
         ├─ YES → Check network requests
         │          ↓
         │      Response status code?
         │         ├─ 503 → Add retry/Mock
         │         └─ Timeout → Increase wait time
         │
         └─ NO → Check assertion
                   ↓
               Mismatched values?
                  ├─ YES → Review expected result
                  └─ NO → Element location issue
                           ↓
                       Update selector
```

#### 自动化检测脚本

```bash
#!/bin/bash
# scripts/detect-flaky.sh

# Run tests multiple times
for i in {1..10}; do
    npx playwright test --reporter=json > report_${i}.json
done

# Analyze results
python scripts/analyze_flakiness.py reports/*.json

# Output:
# flaky_tests.txt (测试列表)
# flaky_analysis.pdf (详细报告)
```

#### 修复模板

**Case 1: Async Operation Timeout**
```typescript
// ❌ WRONG
await page.click('#submit');
await expect(page.getByText('Success')).toBeVisible(); // Might fail

// ✅ FIXED
await page.click('#submit');
await page.waitForResponse(resp => 
  resp.url().includes('/api/submit') && resp.status() === 200
);
await expect(page.getByText('Success')).toBeVisible();
```

**Case 2: Concurrency Issue**
```typescript
// ❌ WRONG (Order-dependent)
test('test A creates user', async () => { ... });
test('test B deletes same user', async () => { ... });  // Depends on A!

// ✅ FIXED (Independent)
test('test A creates unique user', async () => {
  const user = generateUniqueUser();  // Unique each run
});

test('test B deletes its own user', async () => {
  const user = generateUniqueUser();  // Independent from A
});
```

---

### Card #4: 前端性能测试基准

**来源**: Web Vitals + Lighthouse Standards

#### 核心指标阈值

| 指标 | Good (<1s) | Needs Improvement (<2.5s) | Poor (>2.5s) |
|------|------------|-------------------------|--------------|
| **FCP** (First Contentful Paint) | <1.8s | 1.8-3.0s | >3.0s |
| **LCP** (Largest Contentful Paint) | <2.5s | 2.5-4.0s | >4.0s |
| **CLS** (Cumulative Layout Shift) | <0.1 | 0.1-0.25 | >0.25 |
| **TBT** (Total Blocking Time) | <200ms | 200-600ms | >600ms |
| **TTI** (Time to Interactive) | <3.8s | 3.8-7.3s | >7.3s |

#### 自动化测试实现

```typescript
// tests/performance/lighthouse.spec.ts
import { lighthouse } from '@axe-core/playwright';

test.describe('Performance Benchmarks', () => {
  
  test('homepage should meet Lighthouse performance score', async ({ page }) => {
    await page.goto('/');
    
    const { audits } = await page.evaluate(lighthouse, ['/']);
    
    // Performance score threshold
    expect(audits['performance'].numericValue).toBeGreaterThan(90);
    
    // Individual metric checks
    expect(audits['first-contentful-paint'].numericValue).toBeLessThan(1800);
    expect(audits['largest-contentful-paint'].numericValue).toBeLessThan(2500);
    expect(audits['cumulative-layout-shift'].numericValue).toBeLessThan(0.1);
  });
  
  test('dashboard should load within 3 seconds after authentication', async ({ page }) => {
    const startTime = Date.now();
    
    // Simulate login
    await performLogin();
    
    await page.waitForLoadState('networkidle');
    
    const loadTime = Date.now() - startTime;
    expect(loadTime).toBeLessThan(3000);
  });
});
```

---

## 与子技能集成

### devlab-web-test-e2e 引用
```typescript
/**
 * Source: devlab-test-expert/reference/ui-selection-stability.md
 * See also: https://github.com/seed-forge/harness-ai-kit/tree/main/skills/devlab-test-expert
 */
import { semanticSelectors } from '@playwright/test/utils';
```

### devlab-srv-test-api 引用
```typescript
/**
 * Source: devlab-test-expert/reference/api-testing-complete-guide.md
 */
const testCases = require('@test/expert/api-test-cases');
```

---

## 贡献指南

### 添加新知识卡

1. **确定主题覆盖范围** — 确保不与现有卡重复
2. **遵循标准格式** — 使用表格、代码示例、决策树
3. **引用权威来源** — RFC、官方文档、行业白皮书
4. **提供代码示例** — 可执行的 TypeScript/Python 片段
5. **关联相关卡片** — Cross-reference 增强导航

### 审核流程

```
Draft PR → Team Review → Merge to main
         ↓
Update index table in SKILL.md
Update references in sub-skills
```

---

<!-- TRELLIS:START -->
Managed by Trellis. This skill follows the `harness-ai-kit` asset pattern for expert knowledge base.
Last updated: 2026-07-22
Author: AI-assisted knowledge curation based on enterprise best practices.
<!-- TRELLIS:END -->

参考文档：
- references/REFERENCE-README.md
- references/REFERENCE-TEST-DATA-MANAGEMENT.md
- references/REFERENCE-PROPERTY-BASED-TESTING.md
