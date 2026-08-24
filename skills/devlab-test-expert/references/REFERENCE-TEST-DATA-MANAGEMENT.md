# Test Data Management - 企业级测试数据治理完整指南

**核心问题：测试数据从哪里来？怎么生成？如何管理生命周期？**

---

## 1. 数据产生源头分类

### 1.1 主数据来源矩阵

| 来源类型 | 描述 | 优势 | 劣势 | 适用场景 |
|---------|------|------|------|---------|
| **数据库直连** | 直接查询生产/测试库 | 真实数据、约束完整 | 污染风险、性能影响 | 集成测试、复杂查询 |
| **API 调用** | 通过 REST/GraphQL 创建 | 业务逻辑验证、隔离性好 | 速度慢、依赖服务 | E2E 测试、跨服务流程 |
| **UI 创建** | 模拟用户操作生成 | 端到端验证 | 最慢、最脆弱 | 验收测试、用户旅程 |
| **Mock 服务** | 内存中模拟响应 | 快速、可控 | 无法验证真实约束 | 单元测试、外部依赖 |
| **Fixture 文件** | JSON/YAML 静态数据 | 简单、可版本控制 | 维护成本高 | 配置数据、枚举值 |
| **合成数据生成器** | Faker/Factory 动态生成 | 灵活、无副作用 | 需手动维护 schema | 边界值测试、批量数据 |

### 1.2 混合模式决策树

```javascript
// Step 1: 评估测试层级
const testLevel = determineTestLevel();

// Step 2: 选择数据策略
switch (testLevel) {
  case 'UNIT':
    return {
      primary: 'IN_MEMORY_MOCK',
      secondary: 'FIXTURE_FILES',
      tools: ['jest.mock()', 'factory-girl']
    };
    
  case 'INTEGRATION':
    return {
      primary: 'TEST_DATABASE',
      secondary: 'API_SEEDING',
      tools: ['testcontainers', 'supertest']
    };
    
  case 'E2E':
    return {
      primary: 'API_SEEDING',
      secondary: 'UI_CREATION',
      tools: ['@playwright/test', 'msw']
    };
    
  case 'ACCEPTANCE':
    return {
      primary: 'UI_CREATION',
      secondary: 'API_SEEDING',
      tools: ['cypress', 'playwright']
    };
}
```

---

## 2. 数据生成规则引擎

### 2.1 Schema 驱动生成

**核心思想**：从 OpenAPI/JSON Schema 自动推导测试数据

```typescript
// generators/schema-based-generator.ts
import { faker } from '@faker-js/faker';
import Ajv from 'ajv';

interface DataGenerationRule {
  field: string;
  type: 'string' | 'number' | 'boolean' | 'object' | 'array';
  format?: 'email' | 'uuid' | 'date-time' | 'uri';
  constraints: {
    minLength?: number;
    maxLength?: number;
    minimum?: number;
    maximum?: number;
    pattern?: string;
    enum?: any[];
  };
  required: boolean;
}

class SchemaBasedGenerator {
  private ajv = new Ajv();
  
  generateFromSchema(schema: any): Record<string, any> {
    const result: Record<string, any> = {};
    
    for (const [field, definition] of Object.entries(schema.properties)) {
      const rule = this.extractRule(field, definition);
      result[field] = this.generateValue(rule);
    }
    
    return result;
  }
  
  private extractRule(field: string, definition: any): DataGenerationRule {
    return {
      field,
      type: definition.type,
      format: definition.format,
      constraints: {
        minLength: definition.minLength,
        maxLength: definition.maxLength,
        minimum: definition.minimum,
        maximum: definition.maximum,
        pattern: definition.pattern,
        enum: definition.enum
      },
      required: schema.required?.includes(field) || false
    };
  }
  
  private generateValue(rule: DataGenerationRule): any {
    // Handle enum first
    if (rule.constraints.enum) {
      return faker.helpers.arrayElement(rule.constraints.enum);
    }
    
    // Handle by format
    switch (rule.format) {
      case 'email':
        return faker.internet.email();
      case 'uuid':
        return faker.string.uuid();
      case 'date-time':
        return faker.date.recent().toISOString();
      case 'uri':
        return faker.internet.url();
    }
    
    // Handle by type
    switch (rule.type) {
      case 'string':
        return this.generateString(rule.constraints);
      case 'number':
        return this.generateNumber(rule.constraints);
      case 'boolean':
        return faker.datatype.boolean();
      case 'object':
        return {};  // Recursive call needed
      case 'array':
        return [];  // Recursive call needed
    }
  }
  
  private generateString(constraints: any): string {
    const min = constraints.minLength || 5;
    const max = constraints.maxLength || 50;
    
    if (constraints.pattern) {
      // Use pattern-based generation (simplified)
      return faker.string.alphanumeric({ length: { min, max } });
    }
    
    return faker.string.alpha({ length: { min, max } });
  }
  
  private generateNumber(constraints: any): number {
    const min = constraints.minimum || 0;
    const max = constraints.maximum || 1000;
    
    return faker.number.int({ min, max });
  }
}

// Usage example
const userSchema = {
  type: 'object',
  required: ['email', 'name'],
  properties: {
    email: { type: 'string', format: 'email' },
    name: { type: 'string', minLength: 2, maxLength: 100 },
    age: { type: 'number', minimum: 0, maximum: 150 },
    status: { type: 'string', enum: ['active', 'inactive', 'suspended'] }
  }
};

const generator = new SchemaBasedGenerator();
const testUser = generator.generateFromSchema(userSchema);
// Output: { email: 'user@example.com', name: 'John Doe', age: 25, status: 'active' }
```

### 2.2 业务规则约束生成

**场景**：某些字段之间有依赖关系

```typescript
// generators/business-rule-generator.ts

interface BusinessRule {
  condition: (data: any) => boolean;
  transform: (data: any) => any;
  description: string;
}

class BusinessRuleGenerator {
  private rules: BusinessRule[] = [];
  
  addRule(rule: BusinessRule) {
    this.rules.push(rule);
  }
  
  generate(baseData: any): any {
    let result = { ...baseData };
    
    for (const rule of this.rules) {
      if (rule.condition(result)) {
        result = rule.transform(result);
      }
    }
    
    return result;
  }
}

// Example: Order pricing rules
const orderGenerator = new BusinessRuleGenerator();

orderGenerator.addRule({
  description: 'Apply bulk discount for orders > 10 items',
  condition: (data) => data.items.length > 10,
  transform: (data) => ({
    ...data,
    discount: 0.1,  // 10% off
    finalPrice: data.totalPrice * 0.9
  })
});

orderGenerator.addRule({
  description: 'Free shipping for orders > $100',
  condition: (data) => data.totalPrice > 100,
  transform: (data) => ({
    ...data,
    shippingFee: 0
  })
});

orderGenerator.addRule({
  description: 'VIP customers get additional 5% off',
  condition: (data) => data.customerTier === 'VIP',
  transform: (data) => ({
    ...data,
    vipDiscount: 0.05,
    finalPrice: data.finalPrice * 0.95
  })
});

// Generate test order
const testOrder = orderGenerator.generate({
  items: Array(15).fill({ productId: 'SKU-123', price: 10 }),
  totalPrice: 150,
  customerTier: 'VIP'
});

// Output: { items: [...], totalPrice: 150, discount: 0.1, finalPrice: 127.5, shippingFee: 0, vipDiscount: 0.05 }
```

### 2.3 时间序列数据生成

**场景**：需要按时间顺序生成的数据（日志、事件流）

```typescript
// generators/time-series-generator.ts

interface TimeSeriesConfig {
  startTime: Date;
  endTime: Date;
  interval: number;  // milliseconds
  generator: (timestamp: Date) => any;
}

class TimeSeriesGenerator {
  generate(config: TimeSeriesConfig): any[] {
    const results: any[] = [];
    let currentTime = config.startTime.getTime();
    
    while (currentTime <= config.endTime.getTime()) {
      const timestamp = new Date(currentTime);
      results.push(config.generator(timestamp));
      currentTime += config.interval;
    }
    
    return results;
  }
}

// Example: Generate user activity logs
const activityGenerator = new TimeSeriesGenerator();

const activities = activityGenerator.generate({
  startTime: new Date('2026-07-01T00:00:00Z'),
  endTime: new Date('2026-07-22T23:59:59Z'),
  interval: 60 * 60 * 1000,  // Hourly
  generator: (timestamp) => ({
    userId: faker.string.uuid(),
    action: faker.helpers.arrayElement(['login', 'view', 'purchase', 'logout']),
    timestamp: timestamp.toISOString(),
    metadata: {
      ip: faker.internet.ip(),
      userAgent: faker.internet.userAgent()
    }
  })
});

// Output: 528 hourly activity records over 22 days
```

---

## 3. 数据生命周期管理

### 3.1 创建 → 隔离 → 清理流程

```typescript
// lifecycle/data-lifecycle-manager.ts

class DataLifecycleManager {
  private createdResources: Map<string, any> = new Map();
  
  async create<T>(resourceType: string, data: T): Promise<T & { id: string }> {
    // Step 1: Create resource via API
    const response = await test.request.post(`/api/${resourceType}`, {
      data,
      headers: { 'Content-Type': 'application/json' }
    });
    
    const created = await response.json();
    
    // Step 2: Track for cleanup
    this.createdResources.set(`${resourceType}:${created.id}`, created);
    
    return created;
  }
  
  async cleanup(): Promise<void> {
    // Reverse order deletion (dependencies first)
    const resources = Array.from(this.createdResources.entries())
      .sort((a, b) => b[1].createdAt.localeCompare(a[1].createdAt));
    
    for (const [key, resource] of resources) {
      const [type, id] = key.split(':');
      
      try {
        await test.request.delete(`/api/${type}/${id}`);
        console.log(`Cleaned up ${type}:${id}`);
      } catch (error) {
        console.error(`Failed to cleanup ${type}:${id}`, error);
      }
    }
    
    this.createdResources.clear();
  }
}

// Usage in tests
test.describe('User Management', () => {
  const lifecycle = new DataLifecycleManager();
  
  test.beforeEach(async () => {
    // Fresh state for each test
  });
  
  test.afterEach(async () => {
    await lifecycle.cleanup();
  });
  
  test('should create and delete user', async () => {
    const user = await lifecycle.create('users', {
      email: faker.internet.email(),
      name: faker.person.fullName()
    });
    
    // Test operations...
    
    // Cleanup happens automatically in afterEach
  });
});
```

### 3.2 事务回滚策略（Database-level）

```typescript
// lifecycle/transaction-rollback.ts
import { Pool } from 'pg';

class TransactionalTestFixture {
  private pool: Pool;
  private client: any;
  
  async setup() {
    this.pool = new Pool({
      connectionString: process.env.TEST_DATABASE_URL
    });
    
    this.client = await this.pool.connect();
    
    // Start transaction
    await this.client.query('BEGIN');
  }
  
  async teardown() {
    // Rollback all changes
    await this.client.query('ROLLBACK');
    await this.client.release();
  }
  
  async query(sql: string, params?: any[]) {
    return await this.client.query(sql, params);
  }
}

// Usage
test.describe('Database Operations', () => {
  const fixture = new TransactionalTestFixture();
  
  test.beforeEach(async () => {
    await fixture.setup();
  });
  
  test.afterEach(async () => {
    await fixture.teardown();  // All changes rolled back
  });
  
  test('should insert user without affecting other tests', async () => {
    await fixture.query(
      'INSERT INTO users (email, name) VALUES ($1, $2)',
      ['test@example.com', 'Test User']
    );
    
    // Verify insertion
    const result = await fixture.query('SELECT * FROM users WHERE email = $1', ['test@example.com']);
    expect(result.rows.length).toBe(1);
    
    // No cleanup needed - transaction will rollback
  });
});
```

---

## 4. 配套中间件服务架构

### 4.1 独立 Test Data Service（推荐大型项目）

```yaml
# docker-compose.test-data.yml
version: '3.8'

services:
  test-data-service:
    image: team/test-data-service:latest
    ports:
      - "8081:8080"
    environment:
      - DATABASE_URL=postgresql://test:test@postgres:5432/testdb
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis
  
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: testdb
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7-alpine
  
  mock-server:
    image: mockoon/cli:latest
    ports:
      - "3001:3000"
    volumes:
      - ./mocks:/data

volumes:
  postgres_data:
```

### 4.2 Serverless Fixture Manager（轻量级）

```typescript
// serverless/fixture-manager.ts
import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3';

class ServerlessFixtureManager {
  private s3 = new S3Client({ region: 'us-east-1' });
  private bucket = 'test-fixtures';
  
  async saveFixture(name: string, data: any): Promise<string> {
    const key = `fixtures/${Date.now()}-${name}.json`;
    
    await this.s3.send(new PutObjectCommand({
      Bucket: this.bucket,
      Key: key,
      Body: JSON.stringify(data, null, 2),
      ContentType: 'application/json'
    }));
    
    return `s3://${this.bucket}/${key}`;
  }
  
  async loadFixture(uri: string): Promise<any> {
    // Download and parse fixture
    const response = await fetch(uri);
    return await response.json();
  }
}
```

---

## 5. 企业级最佳实践总结

### 5.1 决策矩阵

| 项目规模 | 团队规模 | 推荐方案 | 复杂度 |
|---------|---------|---------|--------|
| 小型 (<10人) | 1-3 人 | In-memory + Faker | ⭐⭐ |
| 中型 (10-50人) | 3-10 人 | Testcontainers + API Seeding | ⭐⭐⭐⭐ |
| 大型 (>50人) | >10 人 | Dedicated Test DB + Microservice | ⭐⭐⭐⭐⭐ |

### 5.2 反模式清单

❌ **绝对禁止**:
- 使用生产数据库副本（数据污染、合规风险）
- 硬编码测试数据（维护噩梦）
- 依赖全局状态（Flaky Test 根源）
- 不清理测试数据（资源泄漏）

✅ **强烈推荐**:
- 每个测试独立 Fixture
- Factory Pattern 生成数据
- 通过 API 创建而非 UI
- before/after hooks 自动清理
- 版本控制 Fixture 文件

---

## 参考资源

- [Testcontainers Documentation](https://www.testcontainers.org/)
- [Factory Girl](https://github.com/aexmachina/factory-girl)
- [Faker.js](https://fakerjs.dev/)
- [MSW (Mock Service Worker)](https://mswjs.io/)
- [Netflix Test Data Management](https://netflixtechblog.com/)

---

<!-- TRELLIS:START -->
Knowledge Card v1.0 for `devlab-test-expert`.
Last updated: 2026-07-22
<!-- TRELLIS:END -->
