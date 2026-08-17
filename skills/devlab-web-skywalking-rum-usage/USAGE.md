# devlab-frontend-skywalking-rum-usage 快速参考

## 安装

```bash
npm install skywalking-client-js
```

## 初始化（30 秒接入）

```typescript
import ClientMonitor from 'skywalking-client-js';

ClientMonitor.register({
  collector: process.env.SW_COLLECTOR_URL,  // OpenResty HTTPS 地址
  service: 'my-app-web',
  serviceVersion: 'v1.0.0',
  pagePath: location.pathname,
  jsErrors: true,
  apiErrors: true,
  resourceErrors: true,
  useWebVitals: true,
  enableSPA: true,
});
```

## 采集能力速查

| 能力 | 参数 | 默认 |
|------|------|------|
| JS 错误 | `jsErrors` | `true` |
| API 错误 | `apiErrors` | `true` |
| 资源错误 | `resourceErrors` | `true` |
| Web Vitals | `useWebVitals` | `false`（需手动开启） |
| SPA 感知 | `enableSPA` | `false`（需手动开启） |
| 自动性能 | `autoTracePerf` | `true` |
| HTTP 详情 | `detailMode` | `true` |

## 验证

```bash
# SkyWalking UI Browser 标签
# http://<overlay-ip>:18080 → Browser
```

## 可直接复制的中文 Prompt

```text
请使用 devlab-web-skywalking-rum-usage 技能，按照其 SKILL.md 描述的标准流程执行任务；
先做 dry-run/检查，向我展示结果与风险，经确认后再正式执行。
```
