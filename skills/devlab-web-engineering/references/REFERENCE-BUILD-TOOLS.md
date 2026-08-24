# 构建工具参考

## 概述

现代前端构建工具各有特点：Webpack（生态完善）、Vite（开发极速）、Rollup（库打包优选）、esbuild（编译速度王）、Parcel（零配置）。本文档说明各工具的配置模式、命令、脚本集成要点。

## Webpack 4/5

### 特征差异

| 特性 | Webpack 4 | Webpack 5 |
|------|-----------|-----------|
| **Module Federation** | ❌ | ✅（微前端原生支持） |
| **持久化缓存** | ❌ | ✅（`cache: {type: 'filesystem'}`） |
| **Tree Shaking** | 基础支持 | 增强支持（usedExports + sideEffects） |
| **Asset Modules** | ❌（需 file-loader/url-loader） | ✅（`type: 'asset'`） |
| **Top Level Await** | ❌ | ✅ |
| **Node Polyfills** | 自动注入 | 手动配置（`resolve.fallback`） |

### 配置文件

```javascript
// webpack.config.js（Webpack 5）
const path = require('path');
const HtmlWebpackPlugin = require('html-webpack-plugin');
const { DefinePlugin } = require('webpack');

module.exports = {
  mode: process.env.NODE_ENV || 'development',
  entry: './src/main.js',
  output: {
    path: path.resolve(__dirname, 'dist'),
    filename: '[name].[contenthash:8].js',
    clean: true, // Webpack 5 清理旧文件
  },
  cache: {
    type: 'filesystem', // 持久化缓存
    cacheDirectory: path.resolve(__dirname, '.webpack-cache'),
  },
  resolve: {
    extensions: ['.js', '.jsx', '.ts', '.tsx', '.vue'],
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  module: {
    rules: [
      {
        test: /\.(js|jsx|ts|tsx)$/,
        exclude: /node_modules/,
        use: 'babel-loader',
      },
      {
        test: /\.vue$/,
        loader: 'vue-loader',
      },
      {
        test: /\.css$/,
        use: ['style-loader', 'css-loader', 'postcss-loader'],
      },
      {
        test: /\.(png|jpe?g|gif|svg|webp)$/i,
        type: 'asset', // Webpack 5 内置
        parser: {
          dataUrlCondition: {
            maxSize: 8 * 1024, // 8KB
          },
        },
      },
    ],
  },
  plugins: [
    new HtmlWebpackPlugin({
      template: './public/index.html',
    }),
    new DefinePlugin({
      'process.env.NODE_ENV': JSON.stringify(process.env.NODE_ENV),
    }),
  ],
  devServer: {
    static: {
      directory: path.join(__dirname, 'public'),
    },
    compress: true,
    port: 3000,
    hot: true,
    historyApiFallback: true, // SPA 路由支持
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        pathRewrite: { '^/api': '' },
      },
    },
  },
};
```

### devServer 配置模式

```javascript
// Webpack 4 风格
devServer: {
  contentBase: './public',
  hot: true,
  port: 3000,
  proxy: {
    '/api': 'http://localhost:8080'
  }
}

// Webpack 5 风格
devServer: {
  static: {
    directory: path.join(__dirname, 'public'),
  },
  hot: true,
  port: 3000,
  proxy: {
    '/api': {
      target: 'http://localhost:8080',
      changeOrigin: true
    }
  }
}
```

### Module Federation（Webpack 5）

```javascript
// 主应用（基座）
const { ModuleFederationPlugin } = require('webpack').container;

module.exports = {
  plugins: [
    new ModuleFederationPlugin({
      name: 'host',
      remotes: {
        app1: 'app1@http://localhost:3001/remoteEntry.js',
        app2: 'app2@http://localhost:3002/remoteEntry.js',
      },
      shared: {
        react: { singleton: true, eager: true },
        'react-dom': { singleton: true, eager: true },
      },
    }),
  ],
};

// 子应用
module.exports = {
  plugins: [
    new ModuleFederationPlugin({
      name: 'app1',
      filename: 'remoteEntry.js',
      exposes: {
        './App': './src/App',
      },
      shared: {
        react: { singleton: true },
        'react-dom': { singleton: true },
      },
    }),
  ],
};
```

### 命令

```bash
# 开发服务器
webpack serve --config webpack.config.js --mode development

# 生产构建
webpack --config webpack.config.js --mode production

# 分析包大小
webpack --config webpack.config.js --profile --json > stats.json
npx webpack-bundle-analyzer stats.json
```

## Vite

### 特征

- **开发服务器**: 基于 esbuild 预构建依赖 + 原生 ESM
- **生产构建**: Rollup（代码分割、Tree Shaking）
- **冷启动**: 极快（不打包，按需编译）
- **HMR**: 毫秒级热更新
- **适用**: Vue 3、React、Svelte、Vanilla JS

### vite.config.js 配置

```javascript
// vite.config.js（Vue 3 示例）
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import path from 'path';

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 3000,
    open: true, // 自动打开浏览器
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
    hmr: {
      overlay: true, // 错误覆盖层
    },
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false,
    minify: 'esbuild', // 或 'terser'
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor': ['vue', 'vue-router', 'pinia'],
          'ui': ['element-plus'],
        },
      },
    },
    chunkSizeWarningLimit: 1000, // KB
  },
  optimizeDeps: {
    include: ['vue', 'vue-router'], // 强制预构建
    exclude: ['@my/local-package'], // 排除预构建
  },
  define: {
    __APP_VERSION__: JSON.stringify('1.0.0'),
  },
});
```

### React + Vite 配置

```javascript
// vite.config.js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [
    react({
      babel: {
        plugins: [
          ['@babel/plugin-proposal-decorators', { legacy: true }],
        ],
      },
    }),
  ],
  server: {
    port: 3000,
  },
});
```

### 环境变量规范

```bash
# .env.local
VITE_APP_TITLE=My App
VITE_API_BASE_URL=http://localhost:8080

# 代码中使用
console.log(import.meta.env.VITE_APP_TITLE);
```

### 命令

```bash
# 开发服务器
vite
HOST="${HOST:-127.0.0.1}" PORT="${PORT:-3000}" vite --host "$HOST" --port "$PORT" --strictPort

# 生产构建
vite build

# 预览生产构建
vite preview
```

### 依赖预构建缓存

```bash
# 清理 Vite 缓存
rm -rf node_modules/.vite

# 强制重新预构建
vite --force
```

## Rollup

### 特征

- **定位**: 库打包首选（生成 ESM/CJS/UMD）
- **Tree Shaking**: 静态分析，按需打包
- **插件系统**: 简洁强大（rollup-plugin-*）
- **代码分割**: 原生支持（动态 import）

### rollup.config.js 配置

```javascript
// rollup.config.js（库打包示例）
import resolve from '@rollup/plugin-node-resolve';
import commonjs from '@rollup/plugin-commonjs';
import babel from '@rollup/plugin-babel';
import { terser } from 'rollup-plugin-terser';
import pkg from './package.json';

export default [
  {
    input: 'src/index.js',
    output: [
      {
        file: pkg.main, // 'dist/index.cjs.js'
        format: 'cjs',
        sourcemap: true,
      },
      {
        file: pkg.module, // 'dist/index.esm.js'
        format: 'esm',
        sourcemap: true,
      },
      {
        file: pkg.unpkg, // 'dist/index.umd.js'
        format: 'umd',
        name: 'MyLib',
        sourcemap: true,
        globals: {
          react: 'React',
        },
      },
    ],
    external: ['react', 'react-dom'], // 不打包的外部依赖
    plugins: [
      resolve(), // 解析 node_modules
      commonjs(), // 转换 CommonJS 模块
      babel({
        babelHelpers: 'bundled',
        exclude: 'node_modules/**',
      }),
      terser(), // 压缩
    ],
  },
];
```

### 应用打包配置

```javascript
// rollup.config.js（应用打包）
import html from '@rollup/plugin-html';
import serve from 'rollup-plugin-serve';
import livereload from 'rollup-plugin-livereload';

export default {
  input: 'src/main.js',
  output: {
    dir: 'dist',
    format: 'esm',
    entryFileNames: '[name].[hash].js',
  },
  plugins: [
    resolve(),
    commonjs(),
    html({
      template: './public/index.html',
    }),
    process.env.NODE_ENV === 'development' && serve('dist'),
    process.env.NODE_ENV === 'development' && livereload('dist'),
  ],
};
```

### 命令

```bash
# 构建
rollup -c

# 监听模式
rollup -c -w

# 指定配置文件
rollup -c rollup.config.prod.js
```

## esbuild

### 特征

- **速度**: 极快（Go 编写，10-100x faster）
- **限制**: 不支持复杂 Webpack 插件、decorator 支持有限
- **适用**: 开发构建、简单库打包、Vite 内部使用

### 配置（build.js）

```javascript
// build.js
const esbuild = require('esbuild');

esbuild.build({
  entryPoints: ['src/index.js'],
  outdir: 'dist',
  bundle: true,
  minify: true,
  sourcemap: true,
  target: 'es2020',
  platform: 'browser', // 或 'node'
  format: 'esm', // 或 'cjs', 'iife'
  loader: {
    '.png': 'file',
    '.svg': 'dataurl',
  },
  define: {
    'process.env.NODE_ENV': '"production"',
  },
  external: ['react', 'react-dom'], // 不打包
}).catch(() => process.exit(1));
```

### 开发服务器

```javascript
// dev-server.js
const esbuild = require('esbuild');

esbuild.serve({
  servedir: 'public',
  port: 3000,
}, {
  entryPoints: ['src/index.js'],
  outdir: 'public/build',
  bundle: true,
  sourcemap: true,
  target: 'es2020',
}).then(server => {
  console.log(`Server running at http://localhost:${server.port}`);
});
```

### 命令

```bash
# 直接构建
esbuild src/index.js --bundle --outfile=dist/bundle.js

# 压缩
esbuild src/index.js --bundle --minify --outfile=dist/bundle.min.js

# 监听模式
esbuild src/index.js --bundle --outfile=dist/bundle.js --watch
```

## Parcel

### 特征

- **零配置**: 自动识别入口、自动安装依赖
- **多核编译**: 并行处理（Worker 线程）
- **适用**: 快速原型、简单应用

### 使用

```json
// package.json
{
  "scripts": {
    "dev": "parcel src/index.html",
    "build": "parcel build src/index.html"
  }
}
```

```bash
# 开发服务器（自动安装缺失依赖）
parcel src/index.html

# 生产构建
parcel build src/index.html --dist-dir dist
```

### 自定义配置（.parcelrc）

```json
{
  "extends": "@parcel/config-default",
  "transformers": {
    "*.vue": ["@parcel/transformer-vue"]
  }
}
```

## 构建工具检测脚本

```bash
detect_build_tool() {
  local project_root="$1"
  
  if [ -f "$project_root/vite.config.js" ] || [ -f "$project_root/vite.config.ts" ]; then
    echo "vite"
  elif [ -f "$project_root/webpack.config.js" ]; then
    echo "webpack"
  elif [ -f "$project_root/rollup.config.js" ]; then
    echo "rollup"
  elif [ -f "$project_root/vue.config.js" ]; then
    echo "vue-cli" # Vue CLI 使用 Webpack
  elif grep -q '"@vue/cli-service"' "$project_root/package.json" 2>/dev/null; then
    echo "vue-cli"
  elif grep -q '"react-scripts"' "$project_root/package.json" 2>/dev/null; then
    echo "cra" # Create React App
  elif grep -q '"next"' "$project_root/package.json" 2>/dev/null; then
    echo "nextjs"
  elif grep -q '"parcel"' "$project_root/package.json" 2>/dev/null; then
    echo "parcel"
  else
    echo "unknown"
  fi
}
```

## 开发服务器配置提取

```bash
extract_dev_server_config() {
  local build_tool="$1"
  local project_root="$2"
  
  case "$build_tool" in
    vite)
      local port=$(grep -oP 'port:\s*\K\d+' "$project_root/vite.config.js" 2>/dev/null || echo "3000")
      echo "port=$port"
      ;;
    webpack|vue-cli)
      local port=$(grep -oP 'port:\s*\K\d+' "$project_root/webpack.config.js" "$project_root/vue.config.js" 2>/dev/null | head -1 || echo "8080")
      echo "port=$port"
      ;;
    cra)
      echo "port=${PORT:-3000}"
      ;;
    nextjs)
      echo "port=3000"
      ;;
    *)
      echo "port=3000"
      ;;
  esac
}
```

## Proxy 配置统一处理

```bash
generate_proxy_config() {
  local build_tool="$1"
  local target_url="$2"
  
  case "$build_tool" in
    vite)
      cat <<EOF
server: {
  proxy: {
    '/api': {
      target: '$target_url',
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/api/, '')
    }
  }
}
EOF
      ;;
    webpack|vue-cli)
      cat <<EOF
devServer: {
  proxy: {
    '/api': {
      target: '$target_url',
      changeOrigin: true,
      pathRewrite: { '^/api': '' }
    }
  }
}
EOF
      ;;
    *)
      warn "未知构建工具，无法生成 proxy 配置"
      ;;
  esac
}
```

## 缓存清理脚本

```bash
clean_build_cache() {
  local project_root="$1"
  
  info "清理构建缓存..."
  
  # Webpack 缓存
  rm -rf "$project_root/.webpack-cache"
  rm -rf "$project_root/node_modules/.cache/webpack"
  
  # Vite 缓存
  rm -rf "$project_root/node_modules/.vite"
  
  # Parcel 缓存
  rm -rf "$project_root/.parcel-cache"
  
  # Next.js 缓存
  rm -rf "$project_root/.next"
  
  # Rollup 缓存（如果使用 rollup-plugin-cache）
  rm -rf "$project_root/.rollup.cache"
  
  success "缓存已清理"
}
```

## 版本检测与推荐

```bash
check_webpack_version() {
  local pkg_json="$1"
  
  if grep -q '"webpack".*"^4\.' "$pkg_json"; then
    warn "检测到 Webpack 4，建议升级到 Webpack 5 以获得更好的性能"
    echo "升级指南: https://webpack.js.org/migrate/5/"
    return 4
  elif grep -q '"webpack".*"^5\.' "$pkg_json"; then
    info "Webpack 5 已安装"
    return 5
  else
    warn "未检测到 Webpack"
    return 0
  fi
}
```

## 参考资料

- [Webpack 官方文档](https://webpack.js.org/)
- [Webpack 5 迁移指南](https://webpack.js.org/migrate/5/)
- [Vite 官方文档](https://vitejs.dev/)
- [Rollup 官方文档](https://rollupjs.org/)
- [esbuild 官方文档](https://esbuild.github.io/)
- [Parcel 官方文档](https://parceljs.org/)
