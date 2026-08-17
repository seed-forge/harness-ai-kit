# React 技术栈参考

## 概述

React 生态系统包含多种脚手架和框架方案，从传统的 Create React App (CRA) 到现代的 Vite、Next.js。本文档覆盖环境变量规范、开发服务器配置、以及不同构建工具的脚本集成要点。

## Create React App (CRA)

### 特征

- **构建工具**: react-scripts（基于 Webpack 5）
- **配置文件**: 零配置（配置隐藏在 react-scripts 中）
- **命令**: `react-scripts start`、`react-scripts build`、`react-scripts test`
- **环境变量规范**: `REACT_APP_*` 前缀（自动注入到客户端）
- **配置暴露**: `npm run eject`（不可逆，暴露所有 Webpack 配置）

### 环境变量规范

```bash
# .env.local 示例
REACT_APP_API_URL=http://localhost:3000/api
REACT_APP_TITLE=My React App
REACT_APP_VERSION=$npm_package_version

# NODE_ENV 由 react-scripts 自动设置
# - npm start → NODE_ENV=development
# - npm run build → NODE_ENV=production
```

```javascript
// 在代码中访问环境变量
const apiUrl = process.env.REACT_APP_API_URL
const isProduction = process.env.NODE_ENV === 'production'

// 未使用 REACT_APP_ 前缀的变量不会被注入
// process.env.MY_SECRET === undefined
```

### 开发服务器配置

CRA 不提供配置文件，但可通过环境变量调整：

```bash
# .env.local
PORT=3000
HOST=0.0.0.0
HTTPS=false
BROWSER=none  # 禁止自动打开浏览器
```

### Proxy 配置

```json
// package.json（简单代理）
{
  "proxy": "http://localhost:5000"
}
```

```javascript
// src/setupProxy.js（复杂代理，需安装 http-proxy-middleware）
const { createProxyMiddleware } = require('http-proxy-middleware')

module.exports = function(app) {
  app.use(
    '/api',
    createProxyMiddleware({
      target: process.env.REACT_APP_API_URL || 'http://localhost:5000',
      changeOrigin: true,
      pathRewrite: {
        '^/api': ''
      },
      logLevel: 'debug'
    })
  )
}
```

### eject 后的配置

```javascript
// config/webpack.config.js（eject 后）
module.exports = {
  devServer: {
    port: process.env.PORT || 3000,
    host: process.env.HOST || 'localhost',
    hot: true,
    compress: true,
    historyApiFallback: {
      disableDotRule: true
    },
    proxy: {
      '/api': {
        target: 'http://backend.example.com',
        changeOrigin: true
      }
    }
  }
}
```

## Vite + React

### 特征

- **构建工具**: Vite 3/4（开发用 esbuild，生产用 Rollup）
- **配置文件**: `vite.config.js` 或 `vite.config.ts`
- **命令**: `vite`、`vite build`、`vite preview`
- **环境变量规范**: `VITE_*` 前缀
- **优势**: 极快的冷启动（ESM）、即时热更新

### 基础配置

```javascript
// vite.config.js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: '0.0.0.0',
    open: false,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom']
        }
      }
    }
  },
  resolve: {
    alias: {
      '@': '/src'
    }
  }
})
```

### 环境变量

```bash
# .env.local
VITE_API_URL=http://localhost:3000/api
VITE_APP_TITLE=My Vite App
```

```javascript
// 在代码中访问
const apiUrl = import.meta.env.VITE_API_URL
const isDev = import.meta.env.DEV
const isProd = import.meta.env.PROD
```

### TypeScript 支持

```typescript
// vite-env.d.ts
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string
  readonly VITE_APP_TITLE: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
```

## Next.js

### 特征

- **类型**: React 全栈框架（SSR/SSG/ISR）
- **路由**: 文件系统路由（`pages/` 或 `app/` 目录）
- **配置文件**: `next.config.js` 或 `next.config.mjs`
- **命令**: `next dev`、`next build`、`next start`
- **环境变量**: `NEXT_PUBLIC_*`（客户端）+ 无前缀（服务端）

### next.config.js 配置

```javascript
// next.config.js
const nextConfig = {
  reactStrictMode: true,
  
  // 环境变量（仅服务端可用）
  env: {
    CUSTOM_KEY: 'my-value'
  },
  
  // 基础路径（部署到子路径）
  basePath: '/app',
  
  // 静态资源前缀
  assetPrefix: process.env.NODE_ENV === 'production' ? 'https://cdn.example.com' : '',
  
  // 自定义 Webpack 配置
  webpack: (config, { isServer }) => {
    if (!isServer) {
      config.resolve.fallback = {
        fs: false,
        net: false
      }
    }
    return config
  },
  
  // 重定向
  async redirects() {
    return [
      {
        source: '/old-path',
        destination: '/new-path',
        permanent: true
      }
    ]
  },
  
  // 代理（仅开发环境）
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:5000/:path*'
      }
    ]
  }
}

module.exports = nextConfig
```

### 环境变量规范

```bash
# .env.local
# 客户端可访问（NEXT_PUBLIC_ 前缀）
NEXT_PUBLIC_API_URL=http://localhost:3000/api
NEXT_PUBLIC_GA_ID=UA-123456789-1

# 仅服务端可访问
DATABASE_URL=postgresql://localhost:5432/mydb
SECRET_KEY=super-secret
```

```javascript
// 客户端代码
const apiUrl = process.env.NEXT_PUBLIC_API_URL  // ✅ 可用

// 服务端代码（API Routes、getServerSideProps 等）
const dbUrl = process.env.DATABASE_URL          // ✅ 可用
const secret = process.env.SECRET_KEY            // ✅ 可用
```

### 页面路由 (Pages Router)

```javascript
// pages/index.js
export default function Home({ data }) {
  return <div>{data.title}</div>
}

// 服务端渲染
export async function getServerSideProps() {
  const res = await fetch(process.env.API_URL)
  const data = await res.json()
  return { props: { data } }
}

// 静态生成
export async function getStaticProps() {
  const res = await fetch('https://api.example.com/data')
  const data = await res.json()
  return {
    props: { data },
    revalidate: 60  // ISR: 每 60 秒重新生成
  }
}
```

### 应用路由 (App Router, Next.js 13+)

```javascript
// app/layout.js
export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}

// app/page.js（服务端组件）
async function getData() {
  const res = await fetch('https://api.example.com/data', {
    next: { revalidate: 60 }
  })
  return res.json()
}

export default async function Page() {
  const data = await getData()
  return <div>{data.title}</div>
}
```

## Webpack Module Federation (微前端)

### 主应用配置

```javascript
// webpack.config.js (Host App)
const ModuleFederationPlugin = require('webpack/lib/container/ModuleFederationPlugin')

module.exports = {
  plugins: [
    new ModuleFederationPlugin({
      name: 'host',
      remotes: {
        app1: 'app1@http://localhost:3001/remoteEntry.js',
        app2: 'app2@http://localhost:3002/remoteEntry.js'
      },
      shared: {
        react: { singleton: true, eager: true },
        'react-dom': { singleton: true, eager: true }
      }
    })
  ]
}
```

### 远程应用配置

```javascript
// webpack.config.js (Remote App)
const ModuleFederationPlugin = require('webpack/lib/container/ModuleFederationPlugin')

module.exports = {
  plugins: [
    new ModuleFederationPlugin({
      name: 'app1',
      filename: 'remoteEntry.js',
      exposes: {
        './Button': './src/components/Button',
        './App': './src/App'
      },
      shared: {
        react: { singleton: true },
        'react-dom': { singleton: true }
      }
    })
  ],
  devServer: {
    port: 3001,
    headers: {
      'Access-Control-Allow-Origin': '*'
    }
  }
}
```

### Next.js + Module Federation

```javascript
// next.config.js（需安装 @module-federation/nextjs-mf）
const NextFederationPlugin = require('@module-federation/nextjs-mf')

module.exports = {
  webpack(config, options) {
    const { isServer } = options
    config.plugins.push(
      new NextFederationPlugin({
        name: 'next_host',
        remotes: {
          remote1: `remote1@http://localhost:3001/_next/static/${isServer ? 'ssr' : 'chunks'}/remoteEntry.js`
        },
        filename: 'static/chunks/remoteEntry.js',
        shared: {}
      })
    )
    return config
  }
}
```

## 脚本集成要点

### 1. 构建工具识别

```bash
detect_react_build_tool() {
  local pkg="$1/package.json"
  
  if grep -q '"next"' "$pkg"; then
    echo "nextjs"
  elif grep -q '"react-scripts"' "$pkg"; then
    echo "cra"
  elif grep -q '"vite"' "$pkg" && grep -q '"@vitejs/plugin-react"' "$pkg"; then
    echo "vite"
  elif [ -f "$1/webpack.config.js" ]; then
    echo "webpack-custom"
  else
    echo "unknown"
  fi
}
```

### 2. 开发服务器启动

```bash
start_react_dev() {
  local build_tool="$1"
  local port="${PORT:-3000}"
  
  case "$build_tool" in
    cra)
      PORT="$port" react-scripts start
      ;;
    vite)
      vite --port "$port" --host 0.0.0.0
      ;;
    nextjs)
      next dev -p "$port"
      ;;
    webpack-custom)
      npm run start -- --port "$port"
      ;;
    *)
      error "未知构建工具: $build_tool"
      exit 1
      ;;
  esac
}
```

### 3. 环境变量前缀检测

```bash
detect_env_prefix() {
  local build_tool="$1"
  
  case "$build_tool" in
    cra)
      echo "REACT_APP_"
      ;;
    vite)
      echo "VITE_"
      ;;
    nextjs)
      echo "NEXT_PUBLIC_"
      ;;
    *)
      echo "REACT_APP_"
      ;;
  esac
}
```

### 4. .env 文件模板生成

```bash
generate_react_env() {
  local build_tool="$1"
  local prefix=$(detect_env_prefix "$build_tool")
  
  cat > .env.local <<EOF
# Generated by devlab-web-bootstrap
# Build Tool: $build_tool

# Server Port
PORT=3000

# API Configuration
${prefix}API_URL=http://localhost:5000/api
${prefix}API_TIMEOUT=30000

# App Configuration
${prefix}APP_NAME=My React App
${prefix}APP_VERSION=1.0.0

# Feature Flags
${prefix}ENABLE_DEBUG=true
EOF
}
```

### 5. Next.js 特殊处理

```bash
# 检测 Pages Router vs App Router
detect_nextjs_router() {
  local project_root="$1"
  
  if [ -d "$project_root/app" ]; then
    echo "app-router"
  elif [ -d "$project_root/pages" ]; then
    echo "pages-router"
  else
    echo "unknown"
  fi
}

# Next.js 构建命令
build_nextjs() {
  info "构建 Next.js 应用..."
  next build
  
  if [ "$EXPORT_STATIC" = "true" ]; then
    info "导出静态站点..."
    next export
  fi
}
```

## 参考资料

- [Create React App 文档](https://create-react-app.dev/)
- [Vite 官方文档](https://vitejs.dev/)
- [Next.js 文档](https://nextjs.org/docs)
- [Webpack Module Federation](https://webpack.js.org/concepts/module-federation/)
- [http-proxy-middleware](https://github.com/chimurai/http-proxy-middleware)
