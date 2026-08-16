---
name: devlab-integration-fullstack
description: 全栈集成测试专家技能。支持多服务 Docker Compose 部署场景，基于 Testcontainers + Mock Server 实现端到端集成测试。
---

# Full Stack Integration Testing Expert Skill

**专注前后端混合架构的端到端业务流程验证能力。**

覆盖微服务联动、消息队列集成、分布式事务补偿等复杂场景。

---

## 触发条件

当用户提到以下关键词时触发此 Skill：
- "全栈集成测试" / "full stack integration test"
- "微服务端到端流程" / "microservice end-to-end workflow"
- "跨服务数据流" / "cross-service data flow"
- "事件驱动架构测试" / "event-driven architecture testing"
- "分布式事务验证" / "distributed transaction validation"

---

## 技术栈依赖

### 核心 CLI
```bash
# E2E Testing
npm install -D @playwright/test

# Backend Testing
npm install -D jest supertest

# Infrastructure (Testcontainers)
npm install -D @testcontainers/postgresql @testcontainers/redis
```

### AI Agent 初始化
```bash
npx playwright init-agents --loop=claude
```

---

## 功能范围

### Phase 1: 跨服务业务流程映射

**输入**：
- 系统架构图（C4 模型或类似）
- API 契约文档
- 业务流程描述（User Journey）

**输出**：
- `specs/workflows/*.md` — 业务流程规格
- `specs/data-flow.md` — 数据流图谱
- `specs/error-handling.md` — 异常处理场景

#### Step 1.1: 服务拓扑分析

```typescript
// services/service-graph-analyzer.ts

interface Service {
  id: string;
  name: string;
  type: 'api' | 'worker' | 'scheduler';
  endpoints?: Endpoint[];
}

interface Dependency {
  from: string;
  to: string;
  protocol: 'http' | 'grpc' | 'message';
  pattern: 'sync' | 'async' | 'saga';
}

class ServiceGraphAnalyzer {
  analyze(configs: any[]): { services: Service[], dependencies: Dependency[] } {
    const services = config.map(c => ({
      id: c.name,
      name: c.displayName,
      type: this.determineType(c),
      endpoints: this.extractEndpoints(c)
    }));
    
    const dependencies = this.extractDependencies(services, configs);
    
    return { services, dependencies };
  }
  
  extractDependencies(services: Service[], configs: any[]): Dependency[] {
    const deps: Dependency[] = [];
    
    configs.forEach(config => {
      // HTTP dependencies
      if (config.services?.forEach((target: string) => {
        deps.push({
          from: config.name,
          to: target,
          protocol: 'http',
          pattern: 'sync'
        });
      }));
      
      // Message queue dependencies
      if (config.topics?.length > 0) {
        config.topics.forEach(topic => {
          deps.push({
            from: config.name,
            to: topic,
            protocol: 'message',
            pattern: 'async'
          });
        });
      }
    });
    
    return deps;
  }
}
```

#### Step 1.2: 业务流程规格生成

```markdown
# specs/workflows/order-processing.md

## Feature: Order Processing Workflow

### User Story
As a customer, I want to place an order so that I can purchase products.

### System Components Involved
| Component | Role | Type |
|-----------|------|------|
| frontend-app | UI layer | api |
| auth-service | User authentication | api |
| cart-service | Shopping cart management | api |
| inventory-service | Stock verification & reservation | api |
| payment-service | Payment processing | api |
| order-service | Order creation & tracking | api |
| email-worker | Confirmation emails | worker |
| kafka-events | Event bus | message |

### Success Flow

1. **User adds item to cart**
   ```
   frontend -> cart-service: POST /cart/items
   cart-service -> auth-service: GET /users/{id}
   cart-service returns: Cart with item
   ```

2. **Checkout initiation**
   ```
   frontend -> cart-service: POST /cart/checkout
   cart-service -> inventory-service: POST /verify-stock
   inventory-service confirms: Stock available
   ```

3. **Payment processing**
   ```
   frontend -> payment-service: POST /payments
   payment-service -> order-service: POST /orders (create pending)
   payment-service processes card: External gateway
   payment-service -> order-service: PUT /orders/{id}/confirm
   ```

4. **Inventory reservation**
   ```
   inventory-service -> kafka: PUBLISH "order.created"
   email-worker consumes: "order.confirmed"
   ```

5. **Confirmation**
   ```
   email-worker sends email
   frontend shows success page
   ```

### Error Handling Scenarios

| Error | Source | Recovery | Expected Outcome |
|-------|--------|----------|------------------|
| Insufficient stock | inventory-service | Cancel order, refund deposit | Order cancelled |
| Payment failed | payment-service | Allow retry or cancel | Retry allowed |
| Auth token expired | auth-service | Force re-login | Session restored |

### Data Contracts

**Order Creation Request:**
```json
{
  "cartId": "uuid",
  "shippingAddress": {...},
  "paymentMethod": {
    "type": "card",
    "token": "tok_xxx"
  },
  "promoCode": "SAVE10"  // optional
}
```

**Order Confirmation Response:**
```json
{
  "orderId": "uuid",
  "status": "confirmed",
  "totalAmount": 129.99,
  "estimatedDelivery": "2026-07-25T10:00:00Z",
  "trackingNumber": "TRK123456789"
}
```
```

---

### Phase 2: 端到端测试代码生成

**输入**：
- `specs/workflows/*.md` 业务规格
- Seed 数据模板

**输出**：
- `tests/e2e/workflows/*.spec.ts`
- `tests/integration/cross-service/*.spec.ts`
- `tests/fixtures/setup.ts`

#### Step 2.1: 全局环境配置

```typescript
// tests/global-setup.ts
import { test as setup } from '@playwright/test';
import { TestContainers } from 'testcontainers';

setup('prepare global fixtures', async () => {
  // Start containers once per suite
  await TestContainers.start();
  
  // Setup database schema
  await setupDatabase();
  
  // Seed initial data
  await seedTestData();
});

setup.afterAll(async () => {
  // Cleanup containers
  await TestContainers.stop();
});
```

#### Step 2.2: Mock Server 配置

```typescript
// tests/mocks/api-helpers.ts
import { setupServer } from 'msw/node';
import { rest } from 'msw';

export function createExternalAPIMocks() {
  return setupServer(
    // Mock payment gateway
    rest.post('https://api.stripe.com/v1/charges', async (req, res, ctx) => {
      const body = await req.json();
      
      // Simulate random payment failures (5%)
      if (Math.random() < 0.05) {
        return res(
          ctx.status(402),
          ctx.json({ error: { message: 'Card declined' } })
        );
      }
      
      return res(
        ctx.status(200),
        ctx.json({
          id: 'ch_' + Math.random().toString(36).substr(2, 9),
          status: 'succeeded',
          amount: body.amount
        })
      );
    }),
    
    // Mock SMS notification
    rest.post('https://api.twilio.com/2010-04-01/Accounts/*/Messages', (req, res, ctx) => {
      return res(
        ctx.status(201),
        ctx.json({ sid: 'SM' + Math.random().toString(36).substr(2, 9) })
      );
    })
  );
}

// In test file
import { createExternalAPIMocks } from '../mocks/api-helpers';
const externalMocks = createExternalAPIMocks();

beforeAll(() => externalMocks.listen());
afterEach(() => externalMocks.resetHandlers());
afterAll(() => externalMocks.close());
```

#### Step 2.3: 跨服务工作流程测试

```typescript
// tests/e2e/workflows/order-processing.spec.ts
import { test, expect } from '../../fixtures';

test.describe('Order Processing E2E', () => {
  
  let userId: string;
  let cartId: string;
  let productId: string;
  
  test.beforeEach(async ({ apiClient }) => {
    // Pre-seed test data
    userId = await apiClient.createUser();
    productId = await apiClient.createProduct({ price: 29.99 });
    await apiClient.addItemToCart(userId, productId, 2);
  });
  
  test('complete order checkout flow with all validations', async ({ 
    page, 
    apiClient,
    mockServer 
  }) => {
    // === STEP 1: Navigate to checkout ===
    await page.goto('/cart');
    await expect(page.getByText('Your Cart')).toBeVisible();
    
    // Verify cart total calculated correctly
    const cartTotal = await page.getByTestId('cart-total').textContent();
    expect(cartTotal).toBe('$59.98');  // 2 * $29.99
    
    // Click checkout button
    await page.getByRole('button', { name: /checkout/i }).click();
    
    // === STEP 2: Shipping information ===
    await expect(page.getByText('Shipping Information')).toBeVisible();
    
    // Fill shipping form
    await page.getByLabel('Email').fill('customer@example.com');
    await page.getByLabel('Address').fill('123 Main St');
    await page.getByLabel('City').fill('New York');
    await page.getByLabel('Zip Code').fill('10001');
    
    // Validate required fields
    await page.getByRole('button', { name: /continue/i }).click();
    await expect(page.getByText('Email is required')).not.toBeVisible();
    
    // Continue to payment
    await page.getByRole('button', { name: /continue to payment/i }).click();
    
    // === STEP 3: Payment processing ===
    await expect(page.getByText('Payment')).toBeVisible();
    
    // Fill credit card info
    await page.getByLabel('Card Number').fill('4111111111111111');
    await page.getByLabel('Expiry Date').fill('12/25');
    await page.getByLabel('CVV').fill('123');
    
    // Apply promo code (if available)
    const promoResponse = page.waitForResponse(resp => 
      resp.url().includes('/api/promo') && resp.status() === 200
    );
    await page.getByLabel('Promo Code').fill('SAVE10');
    await page.getByRole('button', { name: /apply/i }).click();
    await promoResponse;
    
    // Verify discount applied
    const discountElement = await page.getByText(/10% off/i);
    expect(discountElement).toBeVisible();
    
    // Place order
    await page.getByRole('button', { name: /place order/i }).click();
    
    // === STEP 4: Confirm order ===
    await page.waitForLoadState('networkidle');
    
    // Wait for order confirmation modal
    await expect(page.getByText('Order Confirmed')).toBeVisible();
    
    // Capture order ID
    const orderId = await page.getByTestId('order-id').textContent();
    expect(orderId).toBeDefined();
    
    // === VERIFICATIONS ===
    
    // 1. Order created in database
    const order = await apiClient.getOrder(orderId!);
    expect(order.status).toBe('confirmed');
    expect(order.total).toBeLessThan(100);  // Discount applied
    
    // 2. Inventory reserved
    const inventory = await apiClient.getInventory(productId);
    expect(inventory.reserved).toBeGreaterThanOrEqual(2);
    
    // 3. Email sent
    const emailEvents = await mockServer.captureEmails();
    expect(emailEvents).toContainEqual(expect.objectContaining({
      orderId: orderId!,
      template: 'order-confirmation'
    }));
    
    // 4. SMS notification sent (optional)
    const smsEvents = await mockServer.captureSMS();
    // expect(smsEvents.length).toBeGreaterThan(0);  // Can be disabled
    
    // 5. Kafka events published
    const kafkaEvents = await mockServer.consumeTopic('events.order-placed');
    expect(kafkaEvents[0].value.orderId).toBe(orderId!);
    
    // 6. Analytics event tracked
    const analyticsEvents = await page.evaluate(() => window.__ANALYTICS__);
    expect(analyticsEvents[0].eventName).toBe('order_completed');
  });
  
  test('handle insufficient stock gracefully', async ({ page, apiClient }) => {
    // Create product with limited stock
    const lowStockProduct = await apiClient.createProduct({ 
      price: 99.99,
      stock: 1  // Only 1 in stock
    });
    
    await apiClient.addItemToCart(userId, lowStockProduct.id, 2);  // Try to buy 2
    
    await page.goto('/cart');
    
    // Should show warning about quantity limit
    await expect(page.getByText(/only 1 available/i)).toBeVisible();
    
    // Cannot proceed with checkout for 2 items
    await expect(page.getByRole('button', { name: /checkout/i })).toBeDisabled();
  });
  
  test('handle payment failure and allow retry', async ({ 
    page, 
    mockServer 
  }) => {
    // Configure payment gateway to fail
    mockServer.interceptPaymentFailure();
    
    await page.goto('/cart');
    await page.getByRole('button', { name: /checkout/i }).click();
    
    // Fill payment details
    await page.getByLabel('Card Number').fill('4111111111111111');
    await page.getByLabel('Expiry Date').fill('12/25');
    await page.getByLabel('CVV').fill('123');
    
    // Place order (will fail)
    await page.getByRole('button', { name: /place order/i }).click();
    
    // Should show error message but not destroy order draft
    await expect(page.getByText(/payment failed/i)).toBeVisible();
    await expect(page.getByText(/try again/i)).toBeVisible();
    
    // Update payment method
    await page.getByLabel('Card Number').fill('4242424242424242');
    await page.getByRole('button', { name: /retry payment/i }).click();
    
    // Second attempt should succeed
    await expect(page.getByText(/order confirmed/i)).toBeVisible();
  });
  
  test('rollback on inventory timeout', async ({ page, apiClient }) => {
    // Simulate slow inventory service
    mockServer.delayRequest('inventory-service', 10000);
    
    await page.goto('/cart');
    await page.getByRole('button', { name: /checkout/i }).click();
    
    // Should show timeout error
    await expect(page.getByText(/server unavailable/i)).toBeVisible();
    
    // No partial orders should exist
    const pendingOrders = await apiClient.getPendingOrders(userId);
    expect(pendingOrders).toHaveLength(0);
    
    // Cart should still be intact
    await page.goto('/cart');
    await expect(page.getByText('Your Cart')).toBeVisible();
  });
});
```

---

### Phase 3: 分布式事务验证

#### Step 3.1: Saga Pattern 测试

```typescript
// tests/integration/distributed-transactions.spec.ts
import { test, expect } from '../fixtures';

test.describe('Saga Pattern Validation', () => {
  
  test('compensating transaction when payment fails', async ({ 
    apiClient,
    eventStore 
  }) {
    // Arrange: Initiate order
    const order = await apiClient.createOrder({
      items: [{ productId: 'SKU-123', quantity: 1 }],
      status: 'pending_payment'
    });
    
    // Reserve inventory (committed)
    const reservation = await apiClient.reserveInventory(
      order.items[0].productId,
      order.items[0].quantity
    );
    
    // Act: Payment fails, triggers compensation
    await expect(apiClient.processPayment(order.id)).rejects.toThrow('PaymentDeclined');
    
    // Assert: Compensation should release inventory
    const newStock = await apiClient.getStock(order.items[0].productId);
    expect(newStock.available).toBeGreaterThan(reservation.initialStock - reservation.quantity);
    
    // Order status should be cancelled
    const updatedOrder = await apiClient.getOrder(order.id);
    expect(updatedOrder.status).toBe('cancelled');
    
    // Events chain:
    const events = await eventStore.getEventChain(order.id);
    expect(events).toEqual([
      { type: 'ORDER_CREATED', payload: {...order} },
      { type: 'INVENTORY_RESERVED', payload: {...reservation} },
      { type: 'PAYMENT_FAILED', payload: {...error} },
      { type: 'INVENTORY_RELEASED', payload: {...compensation} }  // Compensating transaction
    ]);
  });
  
  test('eventual consistency after eventual updates', async ({
    apiClient,
    waitForEvent
  }) {
    // Create order
    const order = await apiClient.createOrder({ ... });
    
    // Verify immediate consistency
    expect(await apiClient.getOrder(order.id)).toBeDefined();
    
    // Wait for eventual consistency (email notification)
    await waitForEvent('ORDER_CONFIRMED', { timeout: 5000 });
    
    // Email should be sent
    const emails = await apiClient.getEmailsFor(order.userId);
    expect(emails).toContainEqual(expect.objectContaining({
      subject: expect.stringContaining('Order Confirmed')
    }));
    
    // Analytics should be updated
    const analytics = await apiClient.getAnalytics('sales');
    expect(analytics.recentOrders).toContain(order.id);
  });
});
```

#### Step 3.2: Two-Phase Commit 模式测试

```typescript
// tests/integration/two-phase-commit.spec.ts

test('two-phase commit with rollback on validation failure', async ({
  dbTransaction
}) => {
  // Begin transaction
  const tx = await dbTransaction.begin();
  
  try {
    // Phase 1: Prepare
    await tx.prepare('UPDATE accounts SET balance = balance - 100 WHERE id = ?');
    await tx.prepare('UPDATE accounts SET balance = balance + 100 WHERE id = ?');
    
    // All prepare statements succeed
    const prepareStatus = await tx.commitPrepare();
    expect(prepareStatus.allCommitted).toBe(true);
    
    // Phase 2: Commit
    await tx.commit();
    
    // Verify final state
    const account1 = await dbTransaction.getBalance('ACC-001');
    const account2 = await dbTransaction.getBalance('ACC-002');
    
    expect(account1.balance).toBe(originalBalance - 100);
    expect(account2.balance).toBe(originalBalance + 100);
    
  } catch (error) {
    // Rollback if any step fails
    await tx.rollback();
    
    // Verify both accounts unchanged
    // ... assertion logic
  }
});
```

---

### Phase 4: 消息队列集成测试

```typescript
// tests/integration/message-queue.spec.ts

test.describe('Event-Driven Architecture', () => {
  
  test('order placement triggers downstream consumers', async ({
    producer,
    consumer
  }) => {
    // Act: Publish order event
    await producer.publish('orders', {
      type: 'ORDER_PLACED',
      payload: { orderId: 'ORD-123', amount: 500 }
    });
    
    // Wait for all consumers to process
    await Promise.all([
      consumer.waitForConsumer('inventory-service', { timeout: 5000 }),
      consumer.waitForConsumer('email-service', { timeout: 5000 }),
      consumer.waitForConsumer('analytics-service', { timeout: 5000 })
    ]);
    
    // Assert: All downstream effects occurred
    const inventoryUpdate = await consumer.checkEvent('inventory-reserved');
    expect(inventoryUpdate.orderId).toBe('ORD-123');
    
    const emailSent = await consumer.checkEvent('confirmation-email-sent');
    expect(emailSent.orderId).toBe('ORD-123');
    
    const analyticsUpdated = await consumer.checkEvent('order-analytics-updated');
    expect(analyticsUpdated.orderId).toBe('ORD-123');
  });
  
  test('dead letter queue on persistent failures', async ({
    producer,
    dlqConsumer
  }) => {
    // Publish invalid event
    await producer.publish('orders', {
      type: 'ORDER_PLACED',
      payload: { orderId: null, amount: -100 }  // Invalid data
    });
    
    // Consumer attempts (3 times) then moves to DLQ
    await dlqConsumer.waitForMessage({ timeout: 10000 });
    
    // Assert: Message in DLQ with original content preserved
    const dlqMessage = await dlqConsumer.getMessage();
    expect(dlqMessage.payload.orderId).toBe(null);
    expect(dlqMessage.errorCount).toBe(3);
    expect(dlqMessage.errorMessage).toBe('Validation failed');
  });
});
```

---

### Phase 5: 性能与压力测试

#### Step 5.1: 基准测试

```typescript
// tests/performance/load-testing.spec.ts
import { chromium } from '@playwright/test';

test.describe('Performance Benchmarks', () => {
  
  test('checkout flow handles 100 concurrent users', async ({ baseURL }) => {
    const browser = await chromium.launch();
    const promises: Promise<any>[] = [];
    
    // Spawn 100 parallel contexts
    for (let i = 0; i < 100; i++) {
      const context = await browser.newContext();
      const page = await context.newPage();
      
      // Each user goes through checkout
      promises.push(
        page.goto('/cart').then(() => page.click('button[type="submit"]'))
      );
    }
    
    // Measure duration
    const startTime = Date.now();
    const results = await Promise.allSettled(promises);
    const duration = Date.now() - startTime;
    
    // Assert performance SLA
    expect(duration).toBeLessThan(5000);  // 5 seconds for 100 users
    expect(results.filter(r => r.status === 'fulfilled')).toBeGreaterThan(95);  // 95% success
    
    // Cleanup
    await browser.close();
  });
});
```

---

## 联调前接口契约实证前置检查

> 来源：Windsurf 会话挖掘（scan-2026-07-27-073234），联调反复返工根因沉淀。

改前端调用/新接入接口前，必须完成三项实证（不靠口头约定/记忆）：

- [ ] **接口存在性 grep 铁证**：全局 grep 后端 Controller 确认接口真实存在；不存在则**显式降级**（禁用入口/给占位提示）而非假装可用。
- [ ] **真实字段实证**：读后端 Controller/VO 真实字段定义（非接口文档可能过时），对齐类型/可空性/嵌套结构。
- [ ] **拦截器解包规则确认**：确认响应是否被统一包装（如 Result<T> 包装/解包拦截器），前端取数路径与之匹配。

违反代价（实测案例）：前端按记忆中的字段名对接 → 反序列化静默失败 → 排查数小时；接口不存在但前端假装可用 → 用户触发后才暴雷。

## 参考资源

### 架构模式库
- [Microservices Patterns](./references/microservices-patterns.md)
- [Saga Choreography vs Orchestration](./references/saga-patterns.md)
- [Event Sourcing Fundamentals](./references/event-sourcing.md)

### 测试策略
- [Cross-Service Testing](./references/cross-service-testing.md)
- [Chaos Engineering Basics](./references/chaos-engineering.md)
- [Contract Testing with Pact](./references/contract-testing.md)

### 工具链
- [Testcontainers Documentation](https://www.testcontainers.org/)
- [Apache Kafka Testing Guide](./references/kafka-testing.md)
- [gRPC Interceptor Testing](./references/grpc-testing.md)

---

<!-- TRELLIS:START -->
Managed by Trellis. This skill follows the `harness-ai-kit` asset pattern for full-stack integration testing specialization.
Last updated: 2026-07-22
Author: AI-assisted implementation based on enterprise best practices.
<!-- TRELLIS:END -->
