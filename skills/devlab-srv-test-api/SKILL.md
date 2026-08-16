---
name: devlab-srv-test-api
description: 后端 API 测试专家技能。支持 Java（JUnit）/ Python（pytest）/ Node.js（supertest + jest）后端项目的接口测试、Mock 服务、测试数据管理。
---

# Service API 测试专家技能

**专注后端微服务 API 的自动化测试能力。**

支持 REST/GraphQL/OpenAPI 规范的接口测试，覆盖身份认证、数据一致性、链路追踪等核心场景。

---

## 触发条件

当用户提到以下关键词时触发此 Skill：
- "API 测试" / "接口测试" / "interface testing"
- "OpenAPI 测试" / "Swagger 测试"
- "微服务集成测试" / "microservice integration test"
- "REST API 验证" / "GraphQL schema test"
- "认证授权测试" / "authn/authz testing"

---

## 技术栈依赖

### 核心 CLI
```bash
# Node.js 环境
npm install -D jest supertest supertest-fetch

# Python 环境（可选）
pip install pytest requests-mock

# Java 环境（可选）
mvn add dependency:rest-assured
```

### 辅助工具
```bash
# Mock Server（推荐）
npm install -D msw

# 数据生成
npm install -D faker @faker-js/faker

# Schema 验证
npm install -D ajv zod
```

---

## 功能范围

### Phase 1: API Schema 分析与测试点提取

**输入**：
- OpenAPI/Swagger YAML 文档
- （可选）现有 API 客户端代码
- （可选）业务需求描述

**输出**：
- `specs/api-endpoints.md` — 接口清单与测试点
- `specs/data-contracts.md` — 数据模型定义
- `specs/auth-scenarios.md` — 认证授权场景

#### Step 1.1: OpenAPI 解析算法

```typescript
interface OpenAPIAnalysis {
  endpoints: {
    method: 'GET' | 'POST' | 'PUT' | 'DELETE';
    path: string;
    operationId: string;
    summary: string;
    parameters: Parameter[];
    requestBody?: RequestBody;
    responses: Response[];
    security?: SecurityRequirement[];
  }[];
  
  schemas: {
    [key: string]: {
      type: 'object' | 'array' | 'string' | 'number' | 'boolean';
      properties?: Record<string, any>;
      required?: string[];
    };
  };
  
  securitySchemes: {
    [key: string]: {
      type: 'apiKey' | 'http' | 'oauth2' | 'openIdConnect';
      scheme?: string;
      bearerFormat?: string;
    };
  };
}
```

#### Step 1.2: 测试用例生成规则

| 维度 | 测试类型 | 示例 |
|------|---------|------|
| **HTTP Method** | CRUD 覆盖 | GET/POST/PUT/DELETE |
| **Authentication** | 权限验证 | 未登录/普通用户/管理员 |
| **Query Params** | 分页过滤排序 | `?limit=10&offset=20` |
| **Path Params** | 边界值验证 | `/users/{invalid-id}` |
| **Request Body** | 必填字段验证 | 缺失 email/password |
| **Response Codes** | 状态码断言 | 200/400/401/404/500 |
| **Data Integrity** | 一致性校验 | POST after GET shows new record |

#### Step 1.3: 输出测试计划

```markdown
# specs/api-endpoints.md

## POST /api/users - 创建用户

### 测试场景
1. ✅ 有效数据创建成功 (201)
2. ✅ 缺少必填字段返回 400
3. ✅ 邮箱格式错误返回 400
4. ✅ 密码强度不足返回 400
5. ✅ 重复邮箱返回 409
6. ✅ 未认证请求返回 401

### 请求示例
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "name": "John Doe"
}
```

### 响应示例
```json
{
  "id": "uuid-1234",
  "email": "user@example.com",
  "name": "John Doe",
  "status": "active",
  "createdAt": "2026-07-22T10:00:00Z"
}
```
```

---

### Phase 2: API 测试代码生成

**输入**：
- `specs/api-endpoints.md` 测试计划
- 基础测试配置模板

**输出**：
- `tests/api/users.spec.ts`
- `tests/api/auth.spec.ts`
- `tests/integration/*.spec.ts`

#### Step 2.1: 基础配置模板

```typescript
// tests/api/setup.ts
import { test as base, expect } from '@playwright/test';
import { faker } from '@faker-js/faker';

// ========================================
// Type Definitions
// ========================================

interface UserTestData {
  email: string;
  password: string;
  name: string;
}

interface APITestFixtures {
  apiRequest: (method: string, url: string, data?: any) => Promise<Response>;
  authHeader: () => Promise<Record<string, string>>;
  createUser: (overrides?: Partial<UserTestData>) => Promise<UserTestData>;
}

// ========================================
// Custom Fixtures
// ========================================

export const test = base.extend<APITestFixtures>({
  apiRequest: async ({ request }, use) => {
    const apiRequest = async (method: string, url: string, data?: any) => {
      const response = await request[method.toLowerCase()](url, {
        data,
        headers: { 'Content-Type': 'application/json' }
      });
      
      return response;
    };
    
    await use(apiRequest);
  },
  
  authHeader: async ({ request }, use) => {
    const authHeader = async () => {
      // Login and get token
      const loginResponse = await request.post('/api/auth/login', {
        data: {
          email: process.env.TEST_ADMIN_EMAIL || 'admin@test.com',
          password: process.env.TEST_ADMIN_PASSWORD || 'Admin123!'
        }
      });
      
      const { token } = await loginResponse.json();
      return { Authorization: `Bearer ${token}` };
    };
    
    await use(authHeader);
  },
  
  createUser: async ({ request }, use) => {
    const createUser = async (overrides?: Partial<UserTestData>) => {
      const userData = {
        email: faker.internet.email(),
        password: 'TestPass123!',
        name: faker.person.fullName(),
        ...overrides
      };
      
      const response = await request.post('/api/users', {
        data: userData,
        headers: { 'Content-Type': 'application/json' }
      });
      
      if (response.status() !== 201) {
        throw new Error(`Failed to create user: ${await response.text()}`);
      }
      
      return userData;
    };
    
    await use(createUser);
  }
});

export { expect };
```

#### Step 2.2: CRUD 测试套件

```typescript
// tests/api/users.spec.ts
import { test, expect } from './setup';
import { faker } from '@faker-js/faker';

test.describe('POST /api/users', () => {
  
  // ========================================
  // Happy Path Tests
  // ========================================
  
  test('should create user with valid data', async ({ apiRequest, createUser }) => {
    const userData = await createUser();
    
    // Verify response structure
    const response = await apiRequest('GET', `/api/users/${userData.email}`);
    expect(response.status()).toBe(200);
    
    const user = await response.json();
    expect(user.email).toBe(userData.email);
    expect(user.name).toBe(userData.name);
    expect(user.status).toBe('active');
  });
  
  test('should return correct response headers', async ({ apiRequest, createUser }) => {
    const userData = await createUser();
    
    const response = await apiRequest('POST', '/api/users', userData);
    
    expect(response.headers()['content-type']).toContain('application/json');
    expect(response.headers()['location']).toContain('/api/users/');
  });
  
  // ========================================
  // Required Fields Validation
  // ========================================
  
  test('should reject request missing email', async ({ apiRequest }) => {
    const response = await apiRequest('POST', '/api/users', {
      name: 'Test User',
      password: 'Test123!'
    });
    
    expect(response.status()).toBe(400);
    
    const error = await response.json();
    expect(error.errors).toContainEqual(
      expect.objectContaining({ field: 'email' })
    );
  });
  
  test('should reject request missing password', async ({ apiRequest }) => {
    const response = await apiRequest('POST', '/api/users', {
      email: faker.internet.email(),
      name: 'Test User'
    });
    
    expect(response.status()).toBe(400);
  });
  
  // ========================================
  // Field Constraints Validation
  // ========================================
  
  test('should reject email with invalid format', async ({ apiRequest }) => {
    const response = await apiRequest('POST', '/api/users', {
      email: 'not-an-email',
      password: 'Test123!',
      name: 'Test User'
    });
    
    expect(response.status()).toBe(400);
  });
  
  test('should reject weak password', async ({ apiRequest }) => {
    const response = await apiRequest('POST', '/api/users', {
      email: faker.internet.email(),
      password: '123',  // Too short
      name: 'Test User'
    });
    
    expect(response.status()).toBe(400);
  });
  
  // ========================================
  // Idempotency Tests
  // ========================================
  
  test('should prevent duplicate creation with same email', async ({ apiRequest, createUser }) => {
    const userData = await createUser();
    
    // Second creation attempt with same email
    const response = await apiRequest('POST', '/api/users', userData);
    
    expect([400, 409]).toContain(response.status());
  });
  
  // ========================================
  // Side Effect Tests
  // ========================================
  
  test('new user should be visible in GET /api/users immediately', async ({ apiRequest, createUser }) => {
    const userData = await createUser();
    
    // Verify in list
    const listResponse = await apiRequest('GET', '/api/users');
    const listData = await listResponse.json();
    
    const foundUser = listData.data.find(u => u.email === userData.email);
    expect(foundUser).toBeDefined();
  });
});

test.describe('GET /api/users/:id', () => {
  
  test('should return user by valid UUID', async ({ apiRequest, createUser }) => {
    const userData = await createUser();
    
    const response = await apiRequest('GET', `/api/users/${userData.email}`);
    
    expect(response.status()).toBe(200);
    const user = await response.json();
    
    expect(user.email).toBe(userData.email);
  });
  
  test('should return 404 for non-existent user', async ({ apiRequest }) => {
    const fakeId = faker.string.uuid();
    
    const response = await apiRequest('GET', `/api/users/${fakeId}`);
    
    expect(response.status()).toBe(404);
  });
  
  test('should exclude sensitive fields (password hash)', async ({ apiRequest, createUser }) => {
    const userData = await createUser();
    
    const response = await apiRequest('GET', `/api/users/${userData.email}`);
    const user = await response.json();
    
    expect(user).not.toHaveProperty('password');
    expect(user).not.toHaveProperty('passwordHash');
  });
});
```

#### Step 2.3: 认证授权测试

```typescript
// tests/api/auth.spec.ts
import { test, expect } from './setup';

test.describe('Authentication & Authorization', () => {
  
  test('should reject requests without authentication', async ({ apiRequest }) => {
    const response = await apiRequest('GET', '/api/users');
    
    expect(response.status()).toBe(401);
  });
  
  test('should allow authenticated requests', async ({ apiRequest, authHeader }) => {
    const headers = await authHeader();
    
    const response = await apiRequest('GET', '/api/users', undefined, {
      headers
    });
    
    expect(response.status()).toBe(200);
  });
  
  test('should enforce role-based access control', async ({ apiRequest, authHeader }) => {
    const headers = await authHeader();
    
    // Regular user cannot access admin endpoint
    const response = await apiRequest('GET', '/api/admin/users', undefined, {
      headers
    });
    
    expect(response.status()).toBe(403);
  });
  
  test('should validate JWT token expiration', async ({ apiRequest }) => {
    const expiredToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...';  // Expired token
    
    const response = await apiRequest('GET', '/api/users', undefined, {
      headers: { Authorization: `Bearer ${expiredToken}` }
    });
    
    expect(response.status()).toBe(401);
  });
});
```

---

### Phase 3: 微服务集成测试

**场景**：跨服务业务流程验证

```typescript
// tests/integration/order-flow.spec.ts
import { test, expect } from './setup';

test.describe('Order Processing Workflow', () => {
  
  test.beforeEach(async ({ request }) => {
    // Ensure all services are healthy
    await expectServiceHealthy('auth-service');
    await expectServiceHealthy('inventory-service');
    await expectServiceHealthy('order-service');
    await expectServiceHealthy('payment-service');
  });
  
  test('complete order flow with inventory update', async ({ apiRequest, authHeader }) => {
    const headers = await authHeader();
    
    // Step 1: Check initial inventory
    const initialInventory = await getInventory('SKU-123');
    expect(initialInventory).toBe(10);
    
    // Step 2: Create order
    const orderResponse = await apiRequest('POST', '/api/orders', {
      items: [
        { productId: 'SKU-123', quantity: 2 },
        { productId: 'SKU-456', quantity: 1 }
      ]
    }, { headers });
    
    const order = await orderResponse.json();
    expect(orderResponse.status()).toBe(201);
    
    // Step 3: Process payment
    const paymentResponse = await apiRequest('POST', `/api/payments`, {
      orderId: order.id,
      amount: order.total,
      cardNumber: '4111111111111111'
    }, { headers });
    
    expect(paymentResponse.status()).toBe(200);
    
    // Step 4: Wait for async events to process
    await waitForEvent('order.confirmed', 5000);
    await waitForEvent('inventory.updated', 5000);
    
    // Step 5: Verify final state
    const finalInventory = await getInventory('SKU-123');
    expect(finalInventory).toBe(8);  // 10 - 2 = 8
    
    // Step 6: Verify email was sent
    const emailSent = await checkEmailLog('test@example.com');
    expect(emailSent).toContain('Order confirmation');
  });
});

// Helper functions
async function getInventory(productId: string): Promise<number> {
  const response = await test.request.get(`/api/inventory/${productId}`);
  const data = await response.json();
  return data.quantity;
}

async function waitForEvent(eventName: string, timeout: number): Promise<void> {
  // Poll event log or use WebSocket
  const startTime = Date.now();
  
  while (Date.now() - startTime < timeout) {
    const events = await getRecentEvents();
    if (events.some(e => e.type === eventName)) {
      return;
    }
    await new Promise(r => setTimeout(r, 100));
  }
  
  throw new Error(`Event ${eventName} not received within ${timeout}ms`);
}
```

---

### Phase 4: Mock Server 集成

**目的**：隔离外部依赖，加速测试执行

```typescript
// tests/mocks/setup.ts
import { setupServer } from 'msw/node';
import { rest } from 'msw';

export const handlers = [
  // Mock external payment gateway
  rest.post('https://api.stripe.com/charges', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        id: 'ch_mock_123',
        status: 'succeeded',
        amount: 1000
      })
    );
  }),
  
  // Mock email service
  rest.post('https://api.sendgrid.com/mail/send', (req, res, ctx) => {
    return res(ctx.status(202));
  }),
  
  // Mock slow third-party API
  rest.get('https://slow-api.example.com/data', async (req, res, ctx) => {
    await new Promise(r => setTimeout(r, 3000));
    return res(ctx.json({ data: 'mocked' }));
  })
];

export const server = setupServer(...handlers);

// In test setup
beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

---

### Phase 5: 数据一致性验证

**场景**：分布式事务、最终一致性检查

```typescript
test('should maintain data consistency across services', async ({ apiRequest }) => {
  // Create order
  const orderResponse = await apiRequest('POST', '/api/orders', {
    items: [{ productId: 'SKU-123', quantity: 1 }]
  });
  
  const order = await orderResponse.json();
  
  // Wait for eventual consistency (up to 5 seconds)
  await waitForConsistency(async () => {
    const inventoryResponse = await apiRequest('GET', '/api/inventory/SKU-123');
    const inventory = await inventoryResponse.json();
    
    // Inventory should be decremented
    return inventory.quantity === 9;
  }, 5000);
  
  // Verify audit log
  const auditResponse = await apiRequest('GET', `/api/audit?orderId=${order.id}`);
  const auditLog = await auditResponse.json();
  
  expect(auditLog).toContainEqual(
    expect.objectContaining({
      action: 'ORDER_CREATED',
      orderId: order.id
    })
  );
});
```

---

## 参考资源

### 模板库
- [API Test Setup Template](./references/api-test-setup.md)
- [CRUD Test Patterns](./references/crud-test-patterns.md)
- [Auth Testing Strategies](./references/auth-testing-patterns.md)

### 最佳实践
- [OpenAPI Analysis Guide](./references/openapi-analysis.md)
- [Mock Server Integration](./references/mock-server-integration.md)
- [Data Consistency Validation](./references/data-consistency-validation.md)

### 高级主题
- [Distributed Transaction Testing](./references/distributed-transaction-testing.md)
- [Event-Driven Architecture Testing](./references/event-driven-testing.md)
- [Performance Benchmarking](./references/api-performance-benchmarking.md)

---

## 与父级 Skill 集成

### devlab-test-onboard 调用方式
```text
用户："新项目需要配置测试"
  ↓
devlab-test-onboard 检测到项目特征：OpenAPI spec + k8s/
  ↓
自动推荐：devlab-srv-test-api
  ↓
执行命令：
  1. npm install -D jest supertest msw
  2. 生成基础测试模板
  3. 配置 Mock Server
```

### 引用共享资源
```markdown
<!-- 在测试代码中添加引用注释 -->
/**
 * Fixture Library Reference
 * Source: vendored API-request factory fixture (adapted from an internal fixture library)
 * (Fixture pattern adapted from an internal test-fixture library.)
 */
import { apiRequestFactory } from './factories';
```

---

## 已知限制

- ⚠️ **不支持 UI 测试**（请使用 `devlab-web-test-e2e`）
- ⚠️ **GraphQL 支持有限**（需手动编写 schema 验证）
- ✅ **支持**所有 RESTful API 和大部分 RPC 协议

---

## 扩展阅读

- [REST API Testing Best Practices](https://www.restapitool.com/blog/rest-api-testing/)
- [OpenAPI Specification](https://spec.openapis.org/oas/v3.0.3)
- [MSW Documentation](https://mswjs.io/docs/)
- [Testcontainers for Databases](https://www.testcontainers.org/)

---

<!-- TRELLIS:START -->
Managed by Trellis. This skill follows the `harness-ai-kit` asset pattern for service API testing specialization.
Last updated: 2026-07-22
Author: AI-assisted implementation based on enterprise best practices.
<!-- TRELLIS:END -->
