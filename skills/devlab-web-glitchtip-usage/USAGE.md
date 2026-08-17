# devlab-frontend-glitchtip-usage 快速参考

## 安装

```bash
npm install @sentry/browser  # 通用
# npm install @sentry/vue    # Vue
# npm install @sentry/react  # React
```

## 初始化

```typescript
import * as Sentry from '@sentry/browser';

Sentry.init({
  dsn: process.env.SENTRY_DSN,
  environment: process.env.APP_ENV,
  release: process.env.APP_VERSION,
  tracesSampleRate: 0.1,
});
```

## Source Map 上传（CI/CD 中执行）

```bash
SENTRY_URL=https://<service-url> \
SENTRY_AUTH_TOKEN=$GLITCHTIP_TOKEN \
npx @sentry/cli sourcemaps inject ./dist && \
npx @sentry/cli sourcemaps upload --release $VERSION ./dist
```

## 验证

```bash
# GlitchTip UI: https://<service-url>
# 触发: Sentry.captureException(new Error('test'))
```

## 可直接复制的中文 Prompt

```text
请使用 devlab-web-glitchtip-usage 技能，按照其 SKILL.md 描述的标准流程执行任务；
先做 dry-run/检查，向我展示结果与风险，经确认后再正式执行。
```
