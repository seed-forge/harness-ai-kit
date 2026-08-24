# Vue.js 技术栈参考

## 概述

Vue.js 生态系统包含多个版本的脚手架工具和构建系统。本文档覆盖 Vue CLI 2/3/4/5、Vite + Vue、以及 qiankun 微前端集成的脚本生成要点。

## Vue CLI 版本差异

### Vue CLI 2.x (vue-webpack-boilerplate)

- **构建工具**: 原生 Webpack 3/4 配置
- **配置文件**: `build/webpack.dev.conf.js`、`build/webpack.prod.conf.js`
- **命令**: `npm run dev`、`npm run build`
- **特点**: 配置文件完全暴露，自由度高但维护成本大

```bash
# 典型脚本结构
npm run dev    # webpack-dev-server --inline --progress
npm run build  # node build/build.js
```

### Vue CLI 3.x/4.x (@vue/cli-service)

- **构建工具**: @vue/cli-service（基于 Webpack 4）
- **配置文件**: `vue.config.js`（零配置可选）
- **命令**: `vue-cli-service serve`、`vue-cli-service build`
- **环境变量规范**: `VUE_APP_*` 前缀（注入到客户端）

```javascript
// vue.config.js 示例
module.exports = {
  devServer: {
    port: process.env.VUE_APP_PORT || 8080,
    proxy: {
      '/api': {
        target: process.env.VUE_APP_BASE_API,
        changeOrigin: true,
        pathRewrite: { '^/api': '' }
      }
    }
  },
  publicPath: process.env.NODE_ENV === 'production' ? '/app/' : '/',
  outputDir: 'dist',
  productionSourceMap: false
}
```

### Vue CLI 5.x

- **构建工具**: @vue/cli-service（基于 Webpack 5）
- **新特性**: Module Federation、持久化缓存、改进的 Tree Shaking
- **迁移要点**: Node.js 12+ 要求、部分插件需升级

### Vite + Vue 3

- **构建工具**: Vite 3/4（开发用 esbuild，生产用 Rollup）
- **配置文件**: `vite.config.js` 或 `vite.config.ts`
- **命令**: `vite`、`vite build`、`vite preview`
- **环境变量规范**: `VITE_*` 前缀

```javascript
// vite.config.js 示例
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://backend.example.com',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: false
  }
})
```

## 脚本集成要点

### 1. 构建工具识别

```bash
# 检测逻辑（从 package.json 推断）
detect_vue_build_tool() {
  local pkg="$1/package.json"
  
  if grep -q '"@vue/cli-service"' "$pkg"; then
    if grep -q '"vue".*"^3\.' "$pkg"; then
      echo "vue-cli-5"
    else
      echo "vue-cli-3-4"
    fi
  elif grep -q '"vite"' "$pkg"; then
    echo "vite"
  elif [ -d "$1/build" ] && [ -f "$1/build/webpack.dev.conf.js" ]; then
    echo "vue-cli-2"
  else
    echo "unknown"
  fi
}
```

### 2. 开发服务器启动

```bash
# dev.sh 片段（适配多版本）
start_dev_server() {
  local build_tool="$1"
  local port="${VUE_APP_PORT:-3000}"
  
  case "$build_tool" in
    vue-cli-2)
      npm run dev -- --port "$port"
      ;;
    vue-cli-3-4|vue-cli-5)
      vue-cli-service serve --port "$port" --mode development
      ;;
    vite)
      HOST="${HOST:-127.0.0.1}" vite --port "$port" --host "$HOST" --strictPort
      ;;
    *)
      error "未知构建工具: $build_tool"
      exit 1
      ;;
  esac
}
```

### 3. 环境变量处理

```bash
# 根据构建工具设置环境变量前缀
setup_env_vars() {
  local build_tool="$1"
  
  if [ "$build_tool" = "vite" ]; then
    # Vite 要求 VITE_* 前缀
    export VITE_PORT="${VUE_APP_PORT:-3000}"
    export VITE_BASE_API="${VUE_APP_BASE_API:-/api}"
  else
    # Vue CLI 要求 VUE_APP_* 前缀
    export VUE_APP_PORT="${VUE_APP_PORT:-3000}"
    export VUE_APP_BASE_API="${VUE_APP_BASE_API:-/api}"
  fi
}
```

### 4. Pre-build 代码生成

某些项目在构建前需要自动生成路由索引、API 定义等。

```bash
# 检测并执行 pre-build 脚本
run_prebuild_hooks() {
  local project_root="$1"
  
  if [ -f "$project_root/scripts/gen-router-index.js" ]; then
    info "执行 pre-build 脚本: gen-router-index.js"
    node "$project_root/scripts/gen-router-index.js"
  fi
  
  # 检测 package.json 中的 prebuild/preserve 钩子
  if grep -q '"prebuild":' "$project_root/package.json"; then
    info "执行 npm prebuild 钩子"
    npm run prebuild
  fi
}
```

## qiankun 微前端集成

### 端口分配策略

微前端架构中，主应用和子应用需要不同端口。

```bash
# 从 qiankun.config.js 提取端口配置
extract_qiankun_ports() {
  local config_file="$1"
  
  if [ ! -f "$config_file" ]; then
    warn "qiankun 配置文件不存在: $config_file"
    return 1
  fi
  
  # 提取子应用 entry 字段中的端口
  grep -oP 'entry:\s*["\x27]http://[^:]+:\K\d+' "$config_file" || echo ""
}

# 端口探测逻辑（当前项目实现）
find_available_port() {
  local base_port="$1"
  local max_attempts=10
  
  for ((i=0; i<max_attempts; i++)); do
    local port=$((base_port + i))
    if ! ss -tlnp 2>/dev/null | grep -q ":$port "; then
      echo "$port"
      return 0
    fi
  done
  
  error "无法在 $base_port-$((base_port + max_attempts)) 范围内找到可用端口"
  return 1
}
```

### qiankun 配置文件示例

```javascript
// packages/emas-app-main/src/data/config/qiankun.config.js
export const START_OPTS = {
  prefetch: true,      // 预加载子应用
  sandbox: true,       // 启用 JS 沙箱
  singular: true       // 单实例模式
}

export const subapps = [
  {
    name: "emas-subapp-integration",
    activeRule: "/integration",
    entry: "http://localhost:21000/",  // 子应用开发服务器地址
    container: "#subapp-container",
    meta: { title: "集成子应用" }
  }
]
```

### 生命周期钩子

```javascript
// 子应用导出生命周期（webpack 配置需设置 libraryTarget: 'umd'）
export async function bootstrap() {
  console.log('[subapp] bootstrap')
}

export async function mount(props) {
  console.log('[subapp] mount', props)
  // 初始化 Vue 实例
}

export async function unmount() {
  console.log('[subapp] unmount')
  // 销毁 Vue 实例
}
```

### Webpack 配置（子应用）

```javascript
// vue.config.js（子应用）
module.exports = {
  devServer: {
    port: 21000,
    headers: {
      'Access-Control-Allow-Origin': '*'  // 允许主应用跨域加载
    }
  },
  configureWebpack: {
    output: {
      library: `subapp-[name]`,
      libraryTarget: 'umd',
      jsonpFunction: `webpackJsonp_subapp_[name]`
    }
  }
}
```

## vue.config.js devServer 配置模板

```javascript
// 完整示例（基于当前项目）
const envConfig = require('./config/dev.env')

module.exports = {
  devServer: {
    port: process.env.VUE_APP_PORT || 3000,
    host: process.env.HOST || '127.0.0.1',
    hot: true,
    open: false,
    compress: true,
    historyApiFallback: {
      rewrites: [
        { from: /^\/$/, to: '/index.html' }
      ]
    },
    proxy: {
      '/emas/ms': {
        target: envConfig.VUE_APP_BASE_API,
        changeOrigin: true,
        logLevel: 'debug'
      }
    },
    // qiankun 需要允许跨域
    headers: {
      'Access-Control-Allow-Origin': '*'
    }
  },
  publicPath: '/emas/',
  outputDir: 'dist',
  productionSourceMap: false,
  lintOnSave: false,  // 大型项目建议关闭（性能）
  
  // Webpack 链式调用（高级用法）
  chainWebpack(config) {
    // 禁用预加载/预取（优化首屏）
    config.plugins.delete('preload')
    config.plugins.delete('prefetch')
    
    // 图片资源处理
    config.module
      .rule('images')
      .test(/\.(jpg|png|gif|jpeg)/)
      .use('url-loader')
      .loader('url-loader')
      .options({
        limit: 20480,  // 20KB 以下转 base64
        name: 'img/[name].[hash:7].[ext]'
      })
  }
}
```

## 项目类型识别

```bash
# 识别 Vue 项目子类型（主应用/子应用/库）
detect_vue_project_type() {
  local pkg="$1/package.json"
  
  # 主应用特征：依赖 qiankun 且有 registerMicroApps
  if grep -q '"qiankun"' "$pkg"; then
    if grep -rq 'registerMicroApps' "$1/src" 2>/dev/null; then
      echo "qiankun-main"
      return
    else
      echo "qiankun-sub"
      return
    fi
  fi
  
  # 库项目：package.json 中有 main/module 字段
  if grep -q '"main":' "$pkg" || grep -q '"module":' "$pkg"; then
    echo "library"
    return
  fi
  
  echo "standalone-app"
}
```

## Monorepo 中的 Vue 应用编排

```bash
# 启动所有 Vue 子应用（按依赖顺序）
start_all_vue_apps() {
  local workspace_root="$1"
  
  # 1. 先启动主应用
  local main_app=$(find "$workspace_root/packages" -name "package.json" \
    -exec grep -l '"qiankun"' {} \; | head -n1 | xargs dirname)
  
  if [ -n "$main_app" ]; then
    info "启动主应用: $(basename "$main_app")"
    (cd "$main_app" && npm run serve &)
    sleep 5  # 等待主应用端口就绪
  fi
  
  # 2. 并行启动子应用
  find "$workspace_root/packages" -name "package.json" | while read -r pkg; do
    local app_dir=$(dirname "$pkg")
    if [ "$app_dir" != "$main_app" ] && grep -q '"serve":' "$pkg"; then
      info "启动子应用: $(basename "$app_dir")"
      (cd "$app_dir" && npm run serve &)
    fi
  done
}
```

## 参考资料

- [Vue CLI 官方文档](https://cli.vuejs.org/)
- [Vite 官方文档](https://vitejs.dev/)
- [qiankun 微前端框架](https://qiankun.umijs.org/)
- [Vue DevServer Proxy 配置](https://webpack.js.org/configuration/dev-server/#devserverproxy)
- [Webpack Module Federation](https://webpack.js.org/concepts/module-federation/)
