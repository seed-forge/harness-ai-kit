---
name: devlab-web-glitchtip-usage
description: 前端 GlitchTip 错误追踪接入技能。凡是用户提到 GlitchTip、Sentry SDK、前端错误聚合、Source Map 上传、JS 错误追踪、Issue 管理时触发。框架无关，支持 Vue/React/Angular/Svelte/原生 JS。
---

# devlab-frontend-glitchtip-usage

为前端应用接入 GlitchTip 错误追踪平台，实现 JS 错误聚合、Source Map 解析、Release 关联和 Issue 管理。GlitchTip 兼容 Sentry SDK，前端零额外学习成本。

## 适用场景

- 为前端应用安装并配置 Sentry SDK（对接 GlitchTip 后端）
- 全局 JS 错误自动捕获和聚合
- Source Map 上传（构建时自动关联）
- Release 版本管理（追踪错误引入版本）
- Issue 分配、状态跟踪、告警通知

## 不适用场景

- GlitchTip 服务部署/运维 → 参考 `GlitchTip 官方部署文档 https://glitchtip.com/documentation`
- 前端性能监控 / Web Vitals → 使用 `devlab-web-skywalking-rum-usage`
- 后端错误追踪 → 使用对应语言的 Sentry SDK（Python/Ruby/Go 等）

## 前置条件

- GlitchTip 5.2+ 已部署（<host>，端口 18000）
- 已创建 GlitchTip 项目并获取 DSN
- 前端项目可使用 npm 安装依赖

## 工作顺序

### 1. 选择 SDK

根据前端框架选择对应的 Sentry SDK：

| 框架 | npm 包 | 特殊能力 |
|------|--------|---------|
| 通用 / 原生 JS | `@sentry/browser` | 基础错误捕获 |
| Vue 3 | `@sentry/vue` | `app.config.errorHandler` 自动集成 |
| React | `@sentry/react` | `ErrorBoundary` 组件 |
| Angular | `@sentry/angular` | `ErrorHandler` provider |
| Svelte | `@sentry/svelte` | Svelte 错误边界 |

```bash
# 以通用 SDK 为例
npm install @sentry/browser --save

# 或框架专用 SDK
npm install @sentry/vue --save      # Vue
npm install @sentry/react --save    # React
```

### 2. 初始化配置

在项目入口文件中初始化 SDK。DSN 通过环境变量注入，**禁止硬编码**。

#### 通用（@sentry/browser）

```typescript
import * as Sentry from '@sentry/browser';

Sentry.init({
  dsn: process.env.SENTRY_DSN,              // GlitchTip DSN
  environment: process.env.APP_ENV,          // dev / staging / production
  release: process.env.APP_VERSION,          // 关联 Source Map
  tracesSampleRate: 0.1,                     // 10% 性能采样
  maxBreadcrumbs: 50,
  beforeSend(event) {
    // 可选：过滤敏感数据
    if (event.request?.headers) {
      delete event.request.headers['Authorization'];
    }
    return event;
  },
});
```

#### Vue 3

```typescript
import * as Sentry from '@sentry/vue';

Sentry.init({
  app,                                        // Vue app 实例
  dsn: import.meta.env.VITE_GLITCHTIP_DSN,
  environment: import.meta.env.VITE_APP_ENV,
  release: import.meta.env.VITE_APP_VERSION,
  integrations: [
    Sentry.browserTracingIntegration({ router }),
  ],
  tracesSampleRate: 0.1,
});
```

#### React

```tsx
import * as Sentry from '@sentry/react';

Sentry.init({
  dsn: process.env.REACT_APP_GLITCHTIP_DSN,
  environment: process.env.REACT_APP_ENV,
  release: process.env.REACT_APP_VERSION,
  integrations: [
    Sentry.browserTracingIntegration(),
    Sentry.replayIntegration(),
  ],
  tracesSampleRate: 0.1,
});

// 使用 ErrorBoundary
<Sentry.ErrorBoundary fallback={<p>An error occurred</p>}>
  <App />
</Sentry.ErrorBoundary>
```

### 3. Source Map 上传

构建时自动上传 Source Map 到 GlitchTip，使错误堆栈指向源码行号。

#### 手动上传

```bash
# 安装 sentry-cli
npm install -g @sentry/cli

# 注入 Source Map 引用
npx @sentry/cli sourcemaps inject ./dist

# 上传
SENTRY_URL=https://<service-url> \
SENTRY_AUTH_TOKEN=${GLITCHTIP_TOKEN} \
npx @sentry/cli sourcemaps upload \
  --release ${VERSION} \
  ./dist
```

#### CI/CD 集成（Woodpecker）

```yaml
# .woodpecker.yml
steps:
  build:
    image: node:20
    commands:
      - npm ci
      - npm run build
      - npm install -g @sentry/cli
      - npx @sentry/cli sourcemaps inject ./dist
      - |
        SENTRY_URL=https://<service-url> \
        SENTRY_AUTH_TOKEN=$GLITCHTIP_TOKEN \
        npx @sentry/cli sourcemaps upload \
          --release $CI_COMMIT_SHA \
          ./dist
    secrets: [glitchtip_token]
```

#### CI/CD 集成（Jenkins）

```groovy
stage('Upload Source Maps') {
    steps {
        sh '''
            npm install -g @sentry/cli
            npx @sentry/cli sourcemaps inject ./dist
            SENTRY_URL=https://<service-url> \
            SENTRY_AUTH_TOKEN=${GLITCHTIP_TOKEN} \
            npx @sentry/cli sourcemaps upload \
                --release ${BUILD_NUMBER} \
                ./dist
        '''
    }
}
```

### 4. Release 管理

每次部署时创建 Release，关联 Source Map 和 commit：

```bash
# 创建 Release
SENTRY_URL=https://<service-url> \
SENTRY_AUTH_TOKEN=${GLITCHTIP_TOKEN} \
npx @sentry/cli releases new ${VERSION}

# 关联 commit（可选）
npx @sentry/cli releases set-commits ${VERSION} --auto

# 标记部署完成
npx @sentry/cli releases finalize ${VERSION}
```

### 5. 验证闭环

1. **GlitchTip UI 检查**：访问 `https://<service-url>`，确认项目已创建
2. **触发测试错误**：
   ```typescript
   // 在浏览器控制台执行
   Sentry.captureException(new Error('Test error from devlab'));
   ```
3. **Issue 列表检查**：确认 GlitchTip 中出现对应 Issue
4. **Source Map 检查**：点击 Issue 详情，确认堆栈指向源码文件名和行号（而非编译后的 bundle）
5. **Release 检查**：确认 Release 列表中显示正确的版本号和 commit 关联

## 推荐输出格式

执行完毕后输出极简回执：**状态**（✅ 成功 / ⚠️ 部分成功 / ❌ 失败）+ **关键结果**（1-2 行，如操作对象、产出位置、下一步）。无需强制套用大表格。


## 约束

- DSN 通过环境变量注入，禁止硬编码到源码
- API Token 仅在 CI/CD 中使用，不存入代码仓库
- Source Map 上传仅在构建阶段执行，不在运行时
- GlitchTip 仅内网可访问（通过 OpenResty 反代）
- `tracesSampleRate` 建议生产环境 ≤ 0.1，避免性能开销
- 每个前端项目对应一个独立的 GlitchTip Project（不要混用）

## 最小完成定义

1. Sentry SDK 已安装并初始化
2. 全局错误自动捕获已生效
3. Source Map 已上传（构建时自动）
4. GlitchTip Issue 列表中出现测试错误
5. 错误堆栈指向源码行号（Source Map 关联成功）
6. Release 版本正确关联

## 配置上下文

1. 用户对话中明确提供的值（最高优先级）
2. `~/.harness-ai-kit/config.yaml` 中 `assets.devlab-frontend-glitchtip-usage` 或 `global` 段
3. `config.defaults.yaml` 中的默认值

如用户未提供且无默认值的 required 字段，**必须主动询问用户**。
