---
name: devlab-web-skywalking-rum-usage
description: 前端 SkyWalking RUM 接入技能。凡是用户提到前端监控、RUM、skywalking-client-js、Web Vitals 采集、浏览器端链路追踪、前端错误上报时触发。框架无关，支持 Vue/React/Angular/Svelte/原生 JS。
---

# devlab-frontend-skywalking-rum-usage

为前端应用接入 SkyWalking RUM（Real User Monitoring），实现 JS 错误监控、API 调用监控、Core Web Vitals 采集、SPA 路由感知和前后端分布式链路追踪。

## 适用场景

- 为前端应用安装并配置 `skywalking-client-js`
- 接入全局 JS 错误捕获（适配各前端框架）
- 采集 Core Web Vitals（LCP / CLS / INP）
- 监控 XHR / Fetch / Axios 等 API 调用的延迟和错误率
- SPA 路由切换时上报 PV 和性能数据
- 通过 `sw8` header 实现浏览器→后端的分布式 trace 关联

## 不适用场景

- SkyWalking OAP 部署/升级/运维 → 使用 `SkyWalking 官方部署文档 https://skywalking.apache.org`
- 后端 Java Agent 接入 → 使用 `你的后端 APM / Java Agent 接入方案`
- 前端错误聚合平台（Source Map / Issue 管理） → 使用 `devlab-web-glitchtip-usage`
- OAP REST 端口反代配置 → 使用 `infra-ingress-ops`

## 前置条件

- SkyWalking OAP 版本 ≥ **10.2.0**（Browser API 必须）
- OpenResty 已配置 RUM 反代（`/browser/perfData/` → OAP REST :12800），含 CORS
- 前端项目可使用 npm 安装依赖

## 工作顺序

### 1. 安装 SDK

```bash
npm install skywalking-client-js --save
```

### 2. 初始化配置

在项目入口文件中初始化 SDK。参数通过环境变量注入，**禁止硬编码**。

```typescript
// src/monitor/skywalking-rum.ts
import ClientMonitor from 'skywalking-client-js';

export function initRum(options: {
  collector: string;   // OpenResty HTTPS 反代地址，如 https://<service-url>
  service: string;     // 应用标识，如 'my-app-web'
  version: string;     // 应用版本号，如 'v1.0.0'
}) {
  ClientMonitor.register({
    collector: options.collector,
    service: options.service,
    serviceVersion: options.version,
    pagePath: location.pathname,
    jsErrors: true,          // JS 运行时错误
    apiErrors: true,         // API 调用错误（XHR/Fetch/Axios/SuperAgent）
    resourceErrors: true,    // 资源加载错误（图片/脚本/样式）
    useWebVitals: true,      // Core Web Vitals（LCP/CLS/INP）
    enableSPA: true,         // SPA hashchange 自动 PV 上报
    noTraceOrigins: [/localhost/, /127\.0\.0\.1/], // 开发环境排除
    traceTimeInterval: 60000, // 上报间隔（ms）
  });
}
```

**环境变量配置示例**：

| 框架 | 环境变量前缀 | 示例 |
|------|-------------|------|
| Vite | `VITE_` | `VITE_SW_COLLECTOR=https://<service-url>` |
| Next.js | `NEXT_PUBLIC_` | `NEXT_PUBLIC_SW_COLLECTOR=...` |
| Create React App | `REACT_APP_` | `REACT_APP_SW_COLLECTOR=...` |
| Vue CLI | `VUE_APP_` | `VUE_APP_SW_COLLECTOR=...` |

### 3. 全局错误捕获

根据前端框架选择对应的错误捕获机制：

#### Vue 3

```typescript
// src/main.ts
import { initRum } from './monitor/skywalking-rum';
import ClientMonitor from 'skywalking-client-js';

initRum({
  collector: import.meta.env.VITE_SW_COLLECTOR,
  service: import.meta.env.VITE_APP_NAME,
  version: import.meta.env.VITE_APP_VERSION,
});

app.config.errorHandler = (error) => {
  ClientMonitor.reportFrameErrors({
    collector: import.meta.env.VITE_SW_COLLECTOR,
    service: import.meta.env.VITE_APP_NAME,
    pagePath: location.href,
    serviceVersion: import.meta.env.VITE_APP_VERSION,
  }, error);
};
```

#### React

```tsx
// src/ErrorBoundary.tsx
import ClientMonitor from 'skywalking-client-js';

class ErrorBoundary extends React.Component {
  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    ClientMonitor.reportFrameErrors({
      collector: process.env.REACT_APP_SW_COLLECTOR!,
      service: process.env.REACT_APP_NAME!,
      pagePath: location.href,
      serviceVersion: process.env.REACT_APP_VERSION!,
    }, error);
  }
  // ... render
}
```

#### Angular

```typescript
// src/app/global-error-handler.ts
import { ErrorHandler, Injectable } from '@angular/core';
import ClientMonitor from 'skywalking-client-js';

@Injectable()
export class GlobalErrorHandler implements ErrorHandler {
  handleError(error: any) {
    ClientMonitor.reportFrameErrors({
      collector: environment.swCollector,
      service: environment.appName,
      pagePath: location.href,
      serviceVersion: environment.appVersion,
    }, error);
  }
}
```

#### 原生 JS / 其他框架

```typescript
// 全局未捕获错误
window.addEventListener('error', (event) => {
  ClientMonitor.reportFrameErrors({
    collector: SW_COLLECTOR_URL,
    service: APP_NAME,
    pagePath: location.href,
    serviceVersion: APP_VERSION,
  }, event.error);
});

// 未处理的 Promise rejection
window.addEventListener('unhandledrejection', (event) => {
  ClientMonitor.reportFrameErrors({
    collector: SW_COLLECTOR_URL,
    service: APP_NAME,
    pagePath: location.href,
    serviceVersion: APP_VERSION,
  }, event.reason);
});
```

### 4. SPA 路由感知

`enableSPA: true` 可自动监听 `hashchange` 事件。对于 History 模式路由（非 hash），需在路由切换时手动上报：

```typescript
// 通用模式：路由切换后调用 setPerformance
function onRouteChange(newPath: string) {
  ClientMonitor.setPerformance({
    collector: SW_COLLECTOR_URL,
    service: APP_NAME,
    serviceVersion: APP_VERSION,
    pagePath: newPath,
    useWebVitals: true,
  });
}
```

各框架路由钩子接入方式：

| 框架 | 路由钩子 |
|------|---------|
| Vue Router | `router.afterEach((to) => onRouteChange(to.fullPath))` |
| React Router | `useEffect(() => onRouteChange(location.pathname), [location])` |
| Angular Router | `router.events.pipe(filter(e => e instanceof NavigationEnd))` |
| Svelte Kit | `afterNavigate(({ url }) => onRouteChange(url.pathname))` |

### 5. 自定义 Tags

按页面或模块维度打标，方便在 SkyWalking UI 中过滤：

```typescript
ClientMonitor.setCustomTags([
  { key: 'module', value: 'user-dashboard' },
  { key: 'env', value: 'production' },
]);
```

### 6. 验证闭环

完成接入后，按以下步骤验证：

1. **SkyWalking UI 检查**：访问 `http://<overlay-ip>:18080`，进入「Browser」标签页，确认前端服务出现
2. **JS 错误检查**：在浏览器控制台触发一个测试错误（`throw new Error('test')`），确认 UI 中可见
3. **Web Vitals 检查**：加载页面后，确认 UI 中出现 LCP / CLS / INP 指标
4. **API 调用检查**：发起一个 API 请求，确认在 UI 中可见请求延迟
5. **分布式 trace 检查**：前端发起请求 → 后端处理 → 在 SkyWalking UI 中确认 trace 包含浏览器端 span

## OpenResty RUM 反代配置

OAP REST 端口不直接暴露到公网，通过 OpenResty 反代 + HTTPS：

```nginx
location /browser/perfData/ {
    # CORS
    add_header 'Access-Control-Allow-Origin' '$http_origin' always;
    add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS' always;
    add_header 'Access-Control-Allow-Headers' 'Content-Type, Authorization' always;
    add_header 'Access-Control-Max-Age' 86400;

    if ($request_method = 'OPTIONS') {
        return 204;
    }

    proxy_pass http://<overlay-ip>:12800;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

## 推荐输出格式

执行完毕后输出极简回执：**状态**（✅ 成功 / ⚠️ 部分成功 / ❌ 失败）+ **关键结果**（1-2 行，如操作对象、产出位置、下一步）。无需强制套用大表格。


## 约束

- `skywalking-client-js` ≥ 1.0.0 要求 OAP ≥ 10.2.0
- `collector` 地址通过环境变量注入，禁止硬编码到源码中
- OAP 不应直接暴露到公网，必须通过 HTTPS 反代
- `noTraceOrigins` 排除 localhost，避免开发环境产生无效 trace
- SDK 自动追踪 XHR / Fetch / Axios / SuperAgent，不需要额外配置
- 前端 trace 通过 `sw8` HTTP header 注入后端请求，后端 SkyWalking Agent 自动关联

## 专题引用

| 文件 | 用途 |
|------|------|
| [REFERENCE-FRAMEWORK-INTEGRATION.md](references/REFERENCE-FRAMEWORK-INTEGRATION.md) | 各前端框架完整集成示例 |
| [REFERENCE-OPENRESTY-RUM-PROXY.md](references/REFERENCE-OPENRESTY-RUM-PROXY.md) | OpenResty RUM 反代完整配置 |

## 最小完成定义

1. `skywalking-client-js` 已安装并初始化
2. 全局错误捕获已配置（适配当前框架）
3. SkyWalking UI → Browser 标签页中出现前端服务
4. 至少一个 JS 错误可在 UI 中展示
5. Core Web Vitals 指标可采集
6. SPA 路由切换可上报 PV

## 配置上下文

1. 用户对话中明确提供的值（最高优先级）
2. `~/.harness-ai-kit/config.yaml` 中 `assets.devlab-frontend-skywalking-rum-usage` 或 `global` 段
3. `config.defaults.yaml` 中的默认值

如用户未提供且无默认值的 required 字段，**必须主动询问用户**。
