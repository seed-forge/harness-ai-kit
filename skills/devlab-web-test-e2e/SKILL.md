---
name: devlab-web-test-e2e
description: Web E2E 测试专家技能。专注 Vue/React 前端项目的浏览器端到端测试能力，基于 Playwright + AI Agent 实现测试计划生成 → 代码生成 → 失败修复的完整闭环。
---

# Web E2E 测试专家技能

**专注 Vue/React 前端项目的浏览器端到端测试能力。**

基于 Playwright + AI Agent 实现从测试计划生成 → 代码生成 → 失败修复的完整闭环。

---

## 触发条件

当用户提到以下关键词时触发此 Skill：
- "Vue/React 组件测试" / "web component test"
- "浏览器自动化测试" / "browser automation"
- "Playwright 测试" / "E2E 测试"
- "视觉回归测试" / "visual regression"
- "Flaky test 治理" / "不稳定测试修复"

---

## 技术栈依赖

### 核心 CLI
```bash
# 必须安装
npm install -D @playwright/test

# 可选增强
npm install -D vitest  # 单元测试补充
```

### AI Agent 初始化
```bash
npx playwright init-agents --loop=claude
# 或
npx playwright init-agents --loop=codex
```

---

## 功能范围

### Phase 1: 测试场景识别与计划生成

**输入**：
- 应用 URL（本地开发环境）
- （可选）PRD/User Story 描述
- （可选）现有测试代码模式参考

**输出**：
- `specs/features/*.md` — 功能测试计划（Gherkin 格式）
- `specs/regression.md` — 视觉回归检查清单
- `specs/performance.md` — 性能基准要求

**工作流程**：

#### Step 1.1: UI 探索分析
```typescript
// AI 自动打开浏览器扫描应用
const page = await context.newPage();
await page.goto('http://localhost:3000');

// 提取关键元素
const elements = await page.locator('button, input, a').all();
const routes = await extractRoutes(page);
```

**输出物**：
```markdown
# UI Structure Analysis
- 路由表：`/, /login, /dashboard, /settings`
- 主要组件：登录表单、导航栏、数据表格、操作按钮
- 交互点：47 个可点击元素，12 个表单字段
```

#### Step 1.2: 生成测试计划
```gherkin
# specs/features/user-authentication.md

Feature: User Authentication
  As a registered user
  I want to log in securely
  So that I can access my account

  Scenario: Successful login with valid credentials
    Given I am on the login page
    When I enter valid email and password
    And I click "Sign In" button
    Then I should see the dashboard
    And I should receive a welcome message
    
  Scenario Outline: Login validation
    When I enter "<email>" as email
    And I submit the form
    Then I should see error "<error_message>"

    Examples:
      | email          | error_message       |
      | invalid        | Invalid email format|
      | empty@         | Invalid email format|
      |                | Email is required   |
```

---

### Phase 2: Playwright 测试代码生成

**输入**：
- `specs/features/*.md` 测试计划
- `tests/seed.spec.ts` 种子测试模板

**输出**：
- `tests/features/auth/login.spec.ts`
- `tests/regression/*.spec.ts`
- `tests/e2e/*.spec.ts`

#### Step 2.1: 种子测试初始化
```typescript
// tests/seed.spec.ts
import { test, expect } from '@playwright/test';

test.use({
  baseURL: process.env.TEST_BASE_URL || 'http://localhost:3000',
  viewport: { width: 1280, height: 720 },
});

test.describe.configure({ mode: 'setup' });

test('prepare authentication fixture', async ({ page }) => {
  await page.goto('/login');
  
  // Verify page loads correctly
  await expect(page.getByLabel(/email|username/i)).toBeVisible();
  await expect(page.getByLabel(/password/i)).toBeVisible();
  
  // Save login utility for other tests
  await page.addInitScript(() => {
    window.__TEST_UTILS__ = {
      goToLogin: async () => {
        await window.location.assign('/login');
      },
      getCurrentUser: () => localStorage.getItem('user')
    };
  });
});

test('seed: ensure clean storage state', async ({ page, context }) => {
  await page.goto('/logout');
  
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
  });
});
```

#### Step 2.2: 生成特性测试
```typescript
// tests/features/auth/login.spec.ts
import { test, expect } from '../../fixtures';
import { TestDataFactory } from '../../utils/data-factory';

test.describe('User Authentication', () => {
  
  let testUser: ReturnType<typeof TestDataFactory.createUser>;
  
  test.beforeEach(async () => {
    // Create unique test user for each scenario
    testUser = TestDataFactory.createUser('login-test');
    
    // Seed data via API
    await test.request.post('/api/users', {
      data: testUser
    });
  });
  
  test('should login successfully with valid credentials', async ({ page }) => {
    // ✅ Semantic selectors (stable against CSS changes)
    const emailInput = page.getByLabel(/email/i);
    const passwordInput = page.getByLabel(/password/i);
    const submitButton = page.getByRole('button', { name: /sign in/i });
    
    // ✅ Fill form
    await emailInput.fill(testUser.email);
    await passwordInput.fill(testUser.password);
    
    // ✅ Click submit
    await submitButton.click();
    
    // ✅ Assert success
    await expect(page.getByText(/welcome|dashboard/i)).toBeVisible();
    await expect(page).toHaveURL(/.*dashboard.*/);
  });
  
  test('should show validation errors for invalid inputs', async ({ page }) => {
    const testCases = [
      { email: 'invalid', expected: 'Invalid email format' },
      { email: '', expected: 'Email is required' }
    ];
    
    for (const { email, expected } of testCases) {
      await page.goto('/login');
      
      await page.getByLabel(/email/i).fill(email);
      await page.getByRole('button', { name: /sign in/i }).click();
      
      await expect(page.getByText(expected)).toBeVisible();
    }
  });
  
  test('should redirect to previous page after successful login', async ({ page }) => {
    // Navigate to protected route first
    await page.goto('/dashboard');
    
    // Should be redirected to login with next parameter
    await expect(page).toHaveURL(/.*login.*next=.*/);
    
    // Login
    await page.getByLabel(/email/i).fill(testUser.email);
    await page.getByLabel(/password/i).fill(testUser.password);
    await page.getByRole('button', { name: /sign in/i }).click();
    
    // Should redirect back to original destination
    await expect(page).toHaveURL('/dashboard');
  });
});
```

#### Step 2.3: 最佳实践注入

| 原则 | 示例 | 说明 |
|------|------|------|
| **语义选择器** | `getByRole`, `getByLabel` | 不依赖 CSS class |
| **显式等待** | `waitForLoadState('networkidle')` | 非硬编码 delay |
| **数据驱动** | `test.each([inputs])` | 避免重复代码 |
| **测试隔离** | `beforeEach`清理状态 | 互不干扰 |
| **Fixture 复用** | `auth`, `dataFactory` | DRY 原则 |

---

### Phase 3: Healer 失败诊断与修复

**输入**：
- 失败的测试结果
- Screenshot/Trace 文件

**输出**：
- 修复建议报告
- （可选）直接提交修复 commit

#### Step 3.1: 失败分类（Classifier）

```typescript
async function classifyFailure(errorLog: string): Promise<TestFailureType> {
  if (errorLog.includes('Element not found')) {
    return {
      type: 'UI_ELEMENT_CHANGED',
      severity: 'MEDIUM',
      fixStrategy: 'UPDATE_LOCATOR',
      explanation: 'DOM 结构变更，需要更新选择器'
    };
  }
  
  if (errorLog.includes('Timeout') && errorLog.includes('waiting')) {
    return {
      type: 'ASYNCHRONOUS_OPERATION',
      severity: 'LOW',
      fixStrategy: 'ADD_WAIT_OR_RETRY',
      explanation: '异步操作未完成，需要智能等待'
    };
  }
  
  if (errorLog.includes('Expectation failed')) {
    return {
      type: 'ASSERTION_MISMATCH',
      severity: 'HIGH',
      fixStrategy: 'REVIEW_ASSERTION',
      explanation: '断言与实际结果不一致，需检查逻辑'
    };
  }
  
  return { type: 'UNKNOWN', severity: 'CRITICAL', fixStrategy: 'MANUAL_REVIEW' };
}
```

#### Step 3.2: 自动修复策略

**Case 1: UI 元素变更**
```typescript
// ❌ OLD - Fragile selector
await page.click('.btn-primary.submit-button.v-btn--contained');

// ✅ NEW - Semantic selector (稳定)
await page.getByRole('button', { name: /submit/i }).click();
```

**Case 2: 异步操作延迟**
```typescript
// ❌ WRONG - Magic number
await page.click('#submit');
await new Promise(r => setTimeout(r, 3000));

// ✅ CORRECT - Smart wait
await page.click('#submit');
await page.waitForResponse(
  resp => resp.url().includes('/api/submit') && resp.status() === 200
);
await expect(page.getByText('Success')).toBeVisible();
```

**Case 3: Flaky Test**
```typescript
// Mark as flaky + Add retry logic
test.describe.configure({ retries: 2 });

test('should handle concurrent operations (FLAKY)', async ({ page }) => {
  test.info().annotations.push({
    type: 'flaky',
    description: 'Intermittent failures due to race condition, tracked in issue #1234'
  });
  
  // Retry-friendly implementation
  for (let i = 0; i < 3; i++) {
    try {
      await performOperation();
      break;
    } catch (error) {
      if (i === 2) throw error;
      await page.waitForTimeout(1000 * (i + 1));
    }
  }
});
```

---

### Phase 4: 视觉回归测试

**配置**：
```typescript
// playwright.config.ts
export default defineConfig({
  screenshot: {
    mode: 'only-on-failure',  // 失败时自动截图
    fullPage: true,
    transitions: 'allow',     // 捕获过渡动画
  },
  
  // Visual testing plugin (可选)
  use: {
    clip: { x: 0, y: 0, width: 1280, height: 720 },
  },
});
```

**执行流程**：
```bash
# First run: Create baseline
npx playwright test --grep "@visual" --update-snapshots

# Subsequent runs: Compare against baseline
npx playwright test --grep "@visual"
```

**报告输出**：
```
Visual Regression Report
✅ Homepage - No differences detected
⚠️ Dashboard - 3% pixel difference (check screenshots/)
❌ Settings Page - Layout shift detected
```

---

### Phase 5: Flaky Test 检测与治理

**自动检测**：
```bash
# Run tests multiple times to detect flakiness
npx playwright test --repeat-each=5 --workers=1
```

**治理策略**：
1. **隔离标记** → `test.fail()` 临时禁用
2. **根本原因分析** → 日志 + Trace 文件审查
3. **修复策略** → 根据分类选择对应方案
4. **回归检查** → 确保没有引入新问题

---

## 参考资源

### 模板库
- [Vue Playwright Seed Template](./references/vue-playwright-seed.md)
- [Data Factory Patterns](./references/data-factory-patterns.md)
- [Auth Fixture Implementation](./references/auth-fixture-template.md)

### 最佳实践
- [Selector Stability Guide](./references/ui-selection-stability.md)
- [Async Operation Handling](./references/async-operation-patterns.md)
- [Flaky Test Tactics](./references/flaky-test-tactics.md)

### 高级主题
- [Performance Baseline Testing](./references/performance-benchmarking.md)
- [Mock Server Setup](./references/mock-server-integration.md)
- [CI/CD Integration Guide](./references/cicd-integration.md)

---

## 与父级 Skill 集成

### devlab-test-onboard 调用方式
```text
用户："新项目需要配置测试"
  ↓
devlab-test-onboard 检测到项目特征：Vue + Vite
  ↓
自动推荐：devlab-web-test-e2e
  ↓
执行命令：
  1. npm install -D @playwright/test
  2. npx playwright init-agents --loop=claude
  3. 生成基础测试模板
```

### 引用共享资源
```markdown
<!-- 在测试代码中添加引用注释 -->
/**
 * Fixture Library Reference
 * Source: vendored Playwright base fixture (adapted from an internal fixture library)
 * (Fixture pattern adapted from an internal test-fixture library.)
 */
import { baseTest, expect } from './fixtures';
```

---

## 探索性测试委托提示词模板（AI Agent 自主 E2E）

> 来源：Windsurf 会话挖掘（scan-2026-07-27-073234），AI Agent 自主跑 Playwright 探索测试实战验证。

委托 AI Agent 做探索性 E2E 测试时，提示词预埋以下绕行手法，避免 Agent 卡死：

| 障碍 | 绕行手法 |
|------|---------|
| 点击目标被遮挡（overlay/toast） | 改点关联 label / 用键盘导航 / 先关掩层再点 |
| 元素 detach（重渲染后 stale） | 重新定位后重试，不复用旧 handle |
| 弹窗/确认框打断流程 | 提前声明 dialog 处理策略（accept/dismiss） |
| 异步加载未完成 | 断言前等待关键元素可见而非固定 sleep |

**委托提示词骨架**：

```text
探索测试 <页面/功能>：逐个交互元素操作并验证反馈。
约束：点击被遮挡时改点 label 或先关掩层；元素 detach 时重新定位重试（最多 2 次）；
每步截图留证；遇阻塞记录障碍+尝试过的绕行手法后继续下一项，不卡死在单点。
输出：通过项/失败项/阻塞项三段清单。
```

## 已知限制

- ⚠️ **不支持纯后端测试**（请使用 `devlab-srv-test-api`）
- ⚠️ **不支持多浏览器并发调试**（需手动配置 `--headed`）
- ✅ **支持**所有主流现代浏览器（Chrome, Firefox, Safari）

---

## 扩展阅读

- [Playwright Official Documentation](https://playwright.dev/docs/intro)
- [QA Wolf Best Practices](https://www.qawolf.com/blog/the-12-best-ai-testing-tools-in-2026)
- [Antfu Vue Testing Handbook](https://vuetesting.com/)
- [Testing Library Philosophy](https://testing-library.com/docs/)

---

<!-- TRELLIS:START -->
Managed by Trellis. This skill follows the `harness-ai-kit` asset pattern for web E2E testing specialization.
Last updated: 2026-07-22
Author: AI-assisted implementation based on enterprise best practices.
<!-- TRELLIS:END -->
