# Monorepo 方案参考

## 概述

Monorepo（单一代码仓库）通过工作区（Workspace）管理多个相互依赖的包，共享依赖、统一工具链。本文档覆盖 Yarn Workspaces、Lerna、pnpm、Turborepo、Nx 的配置与脚本集成要点。

## Yarn Workspaces

### 特征

- **包管理器**: Yarn 1.x（Classic）/ Yarn 3.x（Berry）
- **配置文件**: 根 `package.json` 的 `workspaces` 字段
- **依赖提升**: 默认将共享依赖提升到根 `node_modules`
- **命令**: `yarn workspaces <command>`
- **适用场景**: 中小型 monorepo，简单依赖管理

### Yarn 1.x 配置

```json
// package.json（根目录）
{
  "name": "my-monorepo",
  "private": true,
  "workspaces": [
    "packages/app-*",
    "packages/lib-*",
    "packages/shared"
  ],
  "scripts": {
    "bootstrap": "yarn install",
    "clean": "yarn workspaces foreach --all run clean",
    "build": "yarn workspaces foreach --topological-dev run build",
    "dev": "yarn workspace @my/app-main dev"
  },
  "devDependencies": {
    "lerna": "^7.0.0"
  },
  "packageManager": "yarn@1.22.19"
}
```

### Yarn 3.x (Berry) 配置

```yaml
# .yarnrc.yml
nodeLinker: node-modules  # 或 pnp（Plug'n'Play）

plugins:
  - path: .yarn/plugins/@yarnpkg/plugin-workspace-tools.cjs
    spec: "@yarnpkg/plugin-workspace-tools"

enableGlobalCache: true
```

### 工作区命令

```bash
# 安装所有工作区依赖
yarn install

# 运行特定工作区的脚本
yarn workspace @my/app-main dev
yarn workspace @my/lib-utils build

# 在所有工作区运行脚本
yarn workspaces run test

# 添加依赖到特定工作区
yarn workspace @my/app-main add lodash

# 添加依赖到根工作区
yarn add -W eslint prettier

# 查看工作区信息
yarn workspaces info
```

### 依赖提升机制

```
monorepo/
├── node_modules/          # 提升的共享依赖
│   ├── react@18.2.0
│   ├── lodash@4.17.21
│   └── ...
├── packages/
│   ├── app-main/
│   │   ├── node_modules/  # 仅包含特定版本的依赖
│   │   │   └── axios@0.27.2
│   │   └── package.json   # dependencies: { react: "^18.2.0", axios: "^0.27.2" }
│   └── lib-utils/
│       └── package.json   # dependencies: { react: "^18.2.0", lodash: "^4.17.21" }
└── package.json           # workspaces: ["packages/*"]
```

## Lerna

### 特征

- **定位**: Monorepo 编排工具（配合 Yarn/npm/pnpm）
- **配置文件**: `lerna.json`
- **模式**: 固定模式（Unified）vs 独立模式（Independent）
- **命令**: `lerna bootstrap`、`lerna run`、`lerna version`
- **版本**: Lerna 3.x（社区维护）→ Lerna 7.x（Nx 官方接手）

### lerna.json 配置

```json
// lerna.json（固定模式）
{
  "version": "1.0.0",
  "npmClient": "yarn",
  "useWorkspaces": true,
  "packages": [
    "packages/*"
  ],
  "command": {
    "bootstrap": {
      "hoist": true,
      "npmClientArgs": ["--no-package-lock"]
    },
    "version": {
      "allowBranch": ["main", "dev"],
      "conventionalCommits": true,
      "message": "chore(release): publish %s"
    },
    "publish": {
      "ignoreChanges": ["*.md", "*.test.js"],
      "registry": "http://localhost:4873"
    }
  }
}
```

```json
// lerna.json（独立模式）
{
  "version": "independent",
  "npmClient": "yarn",
  "useWorkspaces": true,
  "packages": ["packages/emas-app-*", "packages/emas-common"],
  "command": {
    "bootstrap": {
      "ci": false,
      "ignore": ["*-common", "*-components"],
      "ignorePrepublish": true
    }
  }
}
```

### Lerna 常用命令

```bash
# 初始化依赖（链接工作区）
lerna bootstrap

# 清理所有 node_modules
lerna clean

# 运行所有包的脚本
lerna run build
lerna run test --stream  # 实时输出日志

# 运行特定包的脚本
lerna run build --scope=@my/app-main
lerna run test --scope=@my/lib-*

# 查看变更的包
lerna changed

# 发布（自动版本号）
lerna publish

# 版本管理（不发布）
lerna version --conventional-commits
```

### Lerna + Yarn Workspaces 集成

```bash
# 检测函数
detect_lerna_and_yarn() {
  local project_root="$1"
  local has_lerna=false
  local has_yarn_ws=false
  
  if [ -f "$project_root/lerna.json" ]; then
    has_lerna=true
  fi
  
  if grep -q '"workspaces"' "$project_root/package.json" 2>/dev/null; then
    has_yarn_ws=true
  fi
  
  if [ "$has_lerna" = true ] && [ "$has_yarn_ws" = true ]; then
    echo "lerna+yarn"
  elif [ "$has_lerna" = true ]; then
    echo "lerna-only"
  elif [ "$has_yarn_ws" = true ]; then
    echo "yarn-only"
  else
    echo "none"
  fi
}

# 初始化依赖
bootstrap_monorepo() {
  local setup_type="$1"
  
  case "$setup_type" in
    lerna+yarn)
      info "使用 Lerna + Yarn Workspaces 初始化..."
      lerna clean --yes
      lerna bootstrap
      ;;
    lerna-only)
      info "使用 Lerna 初始化..."
      lerna bootstrap
      ;;
    yarn-only)
      info "使用 Yarn Workspaces 初始化..."
      yarn install
      ;;
    *)
      info "标准 npm install..."
      npm install
      ;;
  esac
}
```

## pnpm Workspaces

### 特征

- **包管理器**: pnpm 7.x/8.x
- **配置文件**: `pnpm-workspace.yaml`
- **依赖管理**: 符号链接（Symlink）+ 内容寻址存储
- **优势**: 极快的安装速度、严格的依赖隔离（无幻影依赖）
- **注意**: CI 环境需处理符号链接

### pnpm-workspace.yaml 配置

```yaml
# pnpm-workspace.yaml
packages:
  - 'packages/*'
  - 'apps/*'
  - '!**/test/**'
```

### pnpm 命令

```bash
# 安装所有依赖
pnpm install

# 过滤特定工作区
pnpm --filter "@my/app-main" dev
pnpm --filter "@my/lib-*" build

# 递归运行所有工作区脚本
pnpm -r run build
pnpm -r --parallel run dev

# 添加依赖
pnpm --filter "@my/app-main" add react
pnpm add -w eslint  # 添加到根工作区

# 查看依赖树
pnpm list --depth=0
```

### 符号链接结构

```
monorepo/
├── node_modules/
│   ├── .pnpm/                    # 内容寻址存储
│   │   ├── react@18.2.0/
│   │   │   └── node_modules/
│   │   │       └── react/        # 实际文件
│   │   └── lodash@4.17.21/
│   ├── react -> .pnpm/react@18.2.0/node_modules/react  # 符号链接
│   └── @my/
│       └── lib-utils -> ../../packages/lib-utils      # 工作区链接
└── packages/
    ├── app-main/
    │   └── node_modules/
    │       └── @my/
    │           └── lib-utils -> .pnpm/@my+lib-utils@1.0.0/...
    └── lib-utils/
```

### CI 环境符号链接检测

```bash
check_pnpm_symlinks() {
  local node_modules="$1"
  
  if [ ! -d "$node_modules/.pnpm" ]; then
    warn "pnpm 内容寻址存储不存在，可能未正确安装"
    return 1
  fi
  
  # 检测符号链接是否有效
  if [ -L "$node_modules/react" ]; then
    local target=$(readlink "$node_modules/react")
    if [ ! -e "$node_modules/react" ]; then
      error "符号链接损坏: react -> $target"
      return 1
    fi
  fi
  
  info "pnpm 符号链接检查通过"
  return 0
}

# CI 环境修复（强制重新链接）
fix_pnpm_ci() {
  info "CI 环境：重新安装 pnpm 依赖..."
  rm -rf node_modules
  pnpm install --frozen-lockfile
}
```

### .npmrc 配置

```ini
# .npmrc（pnpm 专用配置）
shamefully-hoist=false      # 不提升依赖（严格模式）
strict-peer-dependencies=true
auto-install-peers=false
node-linker=isolated         # 或 hoisted/pnp

# 私有源配置
registry=https://registry.npmmirror.com/
@my:registry=http://verdaccio.example.com:4873/
```

## Turborepo

### 特征

- **定位**: 高性能构建编排工具（基于任务缓存和并行执行）
- **配置文件**: `turbo.json`
- **核心功能**: 任务 Pipeline、增量构建、远程缓存
- **优势**: 极快的构建速度（任务级缓存）

### turbo.json 配置

```json
{
  "$schema": "https://turbo.build/schema.json",
  "pipeline": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": ["dist/**", ".next/**", "build/**"],
      "cache": true
    },
    "test": {
      "dependsOn": ["build"],
      "outputs": ["coverage/**"],
      "cache": true
    },
    "lint": {
      "cache": true
    },
    "dev": {
      "cache": false,
      "persistent": true
    }
  },
  "globalDependencies": [
    ".env",
    "tsconfig.json"
  ],
  "globalEnv": [
    "NODE_ENV",
    "CI"
  ]
}
```

### Pipeline 语法

```json
{
  "pipeline": {
    "build": {
      "dependsOn": [
        "^build"  // 先构建所有依赖的包（拓扑排序）
      ],
      "outputs": ["dist/**"],  // 缓存输出目录
      "inputs": ["src/**"]     // 输入变化时失效缓存
    },
    "deploy": {
      "dependsOn": [
        "build",    // 当前包的 build 任务
        "test"      // 当前包的 test 任务
      ],
      "cache": false
    }
  }
}
```

### Turborepo 命令

```bash
# 运行所有包的 build 任务（并行 + 缓存）
turbo run build

# 运行特定包的任务
turbo run build --filter=@my/app-main

# 强制重新构建（忽略缓存）
turbo run build --force

# 清理缓存
turbo run build --cache-dir=".turbo"

# 查看任务执行计划（不执行）
turbo run build --dry-run

# 远程缓存（需配置 Vercel/自建缓存服务）
turbo run build --remote-cache
```

### 构建顺序检测

```bash
detect_build_order() {
  local project_root="$1"
  
  if [ -f "$project_root/turbo.json" ]; then
    info "检测到 Turborepo，使用 turbo run 编排..."
    turbo run build --filter="./packages/*"
  elif [ -f "$project_root/lerna.json" ]; then
    info "检测到 Lerna，使用拓扑排序构建..."
    lerna run build --stream
  elif [ -f "$project_root/pnpm-workspace.yaml" ]; then
    info "检测到 pnpm Workspaces，使用递归构建..."
    pnpm -r run build
  else
    warn "未检测到 monorepo 工具，按顺序构建所有包..."
    for pkg in packages/*; do
      if [ -d "$pkg" ]; then
        (cd "$pkg" && npm run build)
      fi
    done
  fi
}
```

## Nx

### 特征

- **定位**: 企业级 Monorepo 解决方案（智能构建、依赖图、生成器）
- **配置文件**: `nx.json`、`workspace.json`
- **命令**: `nx run <project>:<target>`
- **优势**: 受影响分析（Affected）、可视化依赖图、插件生态

### nx.json 配置

```json
{
  "npmScope": "my-org",
  "affected": {
    "defaultBase": "main"
  },
  "tasksRunnerOptions": {
    "default": {
      "runner": "nx/tasks-runners/default",
      "options": {
        "cacheableOperations": ["build", "test", "lint"],
        "parallel": 3
      }
    }
  },
  "targetDefaults": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": ["{projectRoot}/dist"]
    }
  }
}
```

### 项目配置

```json
// apps/app-main/project.json
{
  "name": "app-main",
  "sourceRoot": "apps/app-main/src",
  "projectType": "application",
  "targets": {
    "build": {
      "executor": "@nrwl/webpack:webpack",
      "options": {
        "outputPath": "dist/apps/app-main",
        "main": "apps/app-main/src/main.ts"
      }
    },
    "serve": {
      "executor": "@nrwl/webpack:dev-server",
      "options": {
        "buildTarget": "app-main:build",
        "port": 3000
      }
    }
  }
}
```

### Nx 命令

```bash
# 运行特定项目的任务
nx run app-main:build
nx run app-main:serve

# 简写
nx build app-main
nx serve app-main

# 仅构建受影响的项目
nx affected:build
nx affected:test --base=main --head=HEAD

# 可视化依赖图
nx graph

# 查看受影响的项目
nx affected:apps
nx affected:libs
```

### 受影响分析脚本

```bash
build_affected() {
  local base_branch="${1:-main}"
  
  if command -v nx &>/dev/null; then
    info "使用 Nx 受影响分析构建..."
    nx affected:build --base="$base_branch" --head=HEAD --parallel
  else
    warn "未安装 Nx，构建所有项目..."
    nx run-many --target=build --all
  fi
}
```

## 脚本集成要点

### 1. Monorepo 类型检测

```bash
detect_monorepo_type() {
  local project_root="$1"
  
  local has_turborepo=false
  local has_nx=false
  local has_lerna=false
  local has_pnpm_ws=false
  local has_yarn_ws=false
  
  [ -f "$project_root/turbo.json" ] && has_turborepo=true
  [ -f "$project_root/nx.json" ] && has_nx=true
  [ -f "$project_root/lerna.json" ] && has_lerna=true
  [ -f "$project_root/pnpm-workspace.yaml" ] && has_pnpm_ws=true
  grep -q '"workspaces"' "$project_root/package.json" 2>/dev/null && has_yarn_ws=true
  
  if [ "$has_nx" = true ]; then
    echo "nx"
  elif [ "$has_turborepo" = true ]; then
    echo "turborepo"
  elif [ "$has_lerna" = true ] && [ "$has_yarn_ws" = true ]; then
    echo "lerna+yarn"
  elif [ "$has_lerna" = true ] && [ "$has_pnpm_ws" = true ]; then
    echo "lerna+pnpm"
  elif [ "$has_pnpm_ws" = true ]; then
    echo "pnpm"
  elif [ "$has_yarn_ws" = true ]; then
    echo "yarn"
  else
    echo "none"
  fi
}
```

### 2. 工作区包类型识别

```bash
classify_workspace_packages() {
  local project_root="$1"
  local packages_dir="$project_root/packages"
  
  local apps=()
  local libs=()
  
  for pkg_dir in "$packages_dir"/*; do
    if [ ! -d "$pkg_dir" ]; then
      continue
    fi
    
    local pkg_json="$pkg_dir/package.json"
    if [ ! -f "$pkg_json" ]; then
      continue
    fi
    
    local pkg_name=$(jq -r '.name' "$pkg_json")
    
    # 识别应用类型（有 serve/start/dev 脚本）
    if jq -e '.scripts.serve or .scripts.start or .scripts.dev' "$pkg_json" >/dev/null 2>&1; then
      apps+=("$pkg_name")
    else
      libs+=("$pkg_name")
    fi
  done
  
  echo "Apps: ${apps[*]}"
  echo "Libs: ${libs[*]}"
}
```

### 3. 统一依赖安装

```bash
install_monorepo_deps() {
  local monorepo_type="$1"
  
  case "$monorepo_type" in
    nx)
      info "Nx 项目：安装依赖..."
      npm install
      ;;
    turborepo)
      info "Turborepo 项目：安装依赖..."
      npm install  # 或 pnpm install
      ;;
    lerna+yarn)
      info "Lerna + Yarn Workspaces：初始化..."
      lerna bootstrap
      ;;
    lerna+pnpm)
      info "Lerna + pnpm：初始化..."
      pnpm install
      lerna link
      ;;
    pnpm)
      info "pnpm Workspaces：安装依赖..."
      pnpm install
      ;;
    yarn)
      info "Yarn Workspaces：安装依赖..."
      yarn install
      ;;
    *)
      info "标准项目：npm install..."
      npm install
      ;;
  esac
}
```

### 4. 统一构建脚本

```bash
build_all_packages() {
  local monorepo_type="$1"
  
  case "$monorepo_type" in
    nx)
      nx run-many --target=build --all --parallel
      ;;
    turborepo)
      turbo run build
      ;;
    lerna+*)
      lerna run build --stream
      ;;
    pnpm)
      pnpm -r run build
      ;;
    yarn)
      yarn workspaces run build
      ;;
    *)
      for pkg in packages/*; do
        [ -d "$pkg" ] && (cd "$pkg" && npm run build)
      done
      ;;
  esac
}
```

## 参考资料

- [Yarn Workspaces 文档](https://classic.yarnpkg.com/en/docs/workspaces/)
- [Lerna 官方文档](https://lerna.js.org/)
- [pnpm Workspaces](https://pnpm.io/workspaces)
- [Turborepo 文档](https://turbo.build/repo/docs)
- [Nx 官方文档](https://nx.dev/)
