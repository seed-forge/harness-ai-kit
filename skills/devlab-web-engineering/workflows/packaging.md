# Packaging 工作流（打包与交付）

## 触发

- 前端产物容器化（Docker 镜像）
- 静态部署（nginx / CDN）
- 微前端 base/sub-app 交付

## 步骤

```
1. 交付方式判定（Phase 0 扫描结果）
   - 已有 Dockerfile → 沿用并审查；无 → 生成模板
   - 静态部署 → nginx.conf + 产物清单
   - 微前端 → base/sub-app 独立交付

2. 容器化（推荐模板）
   FROM node:20-alpine AS build
   WORKDIR /app
   COPY package.json pnpm-lock.yaml ./
   RUN pnpm install --frozen-lockfile
   COPY . .
   RUN pnpm build

   FROM nginx:alpine
   COPY --from=build /app/dist /usr/share/nginx/html
   COPY nginx.conf /etc/nginx/conf.d/default.conf

3. nginx 要点
   - SPA history 路由 fallback: try_files $uri $uri/ /index.html
   - 静态资源缓存（assets/ 带 hash 长缓存）
   - gzip / brotli

4. 微前端交付
   - 子应用独立 dist + 端口/路由注册清单
   - 主应用按 entry 加载；公共依赖提升防多实例

5. 交付物清单
   - dist 路径 / 镜像 tag / nginx 配置 / 部署说明
   - 部署执行走 devlab-cicd-onboard / 部署管线，本技能只生成命令与配置
```

## 约束

- 不自动执行 `docker build` / 部署命令，仅生成命令供用户确认
- 镜像与部署配置不硬编码主机/凭据（走 devlab-infra-usage）
