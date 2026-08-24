# NPM Registry 策略参考

## 概述

前端项目依赖安装常面临私有源不稳定、二进制包下载失败、镜像源切换等问题。本文档提供统一的 registry 配置、降级策略、二进制包处理方案，可嵌入到生成的 common.sh 脚本中。

## Registry 配置方式

| 方式 | 文件 | 优先级 | 适用包管理器 | 说明 |
|------|------|--------|-------------|------|
| **项目级** | `.npmrc` | 1 | npm, yarn, pnpm | 项目根目录，版本控制 |
| **用户级** | `~/.npmrc` | 2 | npm, yarn, pnpm | 全局默认配置 |
| **命令行** | `--registry` | 0 | npm, yarn, pnpm | 临时指定，优先级最高 |
| **环境变量** | `NPM_CONFIG_REGISTRY` | 3 | npm, yarn, pnpm | 脚本中动态设置 |
| **Yarn 专用** | `.yarnrc` | 1 | yarn 1.x | Yarn Classic 配置 |
| **Yarn 2+ 专用** | `.yarnrc.yml` | 1 | yarn 2+/3+ | Yarn Berry 配置 |

## 私有源配置

### 配置文件模板

**`.npmrc`（项目级）**

```ini
# 主 registry（私有源）
registry=${PRIVATE_REGISTRY}

# 二进制包镜像（node-sass, electron, puppeteer 等）
sass_binary_site=https://npmmirror.com/mirrors/node-sass
electron_mirror=https://npmmirror.com/mirrors/electron/
puppeteer_download_host=https://npmmirror.com/mirrors
chromedriver_cdnurl=https://npmmirror.com/mirrors/chromedriver

# pnpm 专用
shamefully-hoist=true

# 网络配置
fetch-retries=3
fetch-retry-mintimeout=10000
fetch-retry-maxtimeout=60000
```

**`.yarnrc`（Yarn 1.x）**

```ini
registry "${PRIVATE_REGISTRY}"
sass_binary_site "https://npmmirror.com/mirrors/node-sass"
electron_mirror "https://npmmirror.com/mirrors/electron/"
puppeteer_download_host "https://npmmirror.com/mirrors"
```

**`.yarnrc.yml`（Yarn 2+）**

```yaml
npmRegistryServer: "${PRIVATE_REGISTRY}"

npmScopes:
  company:
    npmRegistryServer: "${PRIVATE_REGISTRY}"

supportedArchitectures:
  os: ["linux", "darwin", "win32"]
  cpu: ["x64", "arm64"]
```

### 动态设置 Registry（脚本中）

```bash
# 设置 registry（支持 npm/yarn/pnpm）
set_registry() {
  local registry_url="$1"
  local pkg_manager="${2:-yarn}"
  
  info "设置 registry: $registry_url"
  
  case "$pkg_manager" in
    npm)
      npm config set registry "$registry_url"
      ;;
    yarn)
      yarn config set registry "$registry_url"
      ;;
    pnpm)
      pnpm config set registry "$registry_url"
      ;;
    *)
      error "不支持的包管理器: $pkg_manager"
      return 1
      ;;
  esac
}

# 临时设置 registry（仅当前 shell）
export_registry_env() {
  local registry_url="$1"
  export NPM_CONFIG_REGISTRY="$registry_url"
  info "临时 registry: $NPM_CONFIG_REGISTRY"
}
```

## Registry 探测与降级策略

### 探测私有源可用性

```bash
# 检测 registry 是否可访问
check_registry_available() {
  local registry_url="$1"
  local timeout="${2:-5}"
  
  # 提取域名和端口
  local host_port
  host_port=$(echo "$registry_url" | sed -E 's|https?://||' | cut -d'/' -f1)
  
  info "探测 registry: $registry_url"
  
  # 尝试 HTTP 请求
  if curl -sf --max-time "$timeout" "$registry_url" >/dev/null 2>&1; then
    success "registry 可访问"
    return 0
  else
    warn "registry 不可访问: $registry_url"
    return 1
  fi
}

# 探测 registry 延迟
measure_registry_latency() {
  local registry_url="$1"
  
  local start_time
  local end_time
  local latency
  
  start_time=$(date +%s%3N)
  curl -sf --max-time 5 "$registry_url" >/dev/null 2>&1
  end_time=$(date +%s%3N)
  
  latency=$((end_time - start_time))
  echo "$latency"
}
```

### 降级策略（私有源 → 公共镜像 → 官方源）

```bash
# Registry 降级列表
REGISTRY_FALLBACK_LIST=(
  "${PRIVATE_REGISTRY}"                    # 私有源
  "https://registry.npmmirror.com"           # 国内镜像（淘宝）
  "https://registry.npmjs.org"               # 官方源
)

# 选择可用的 registry
select_available_registry() {
  local selected_registry=""
  
  for registry in "${REGISTRY_FALLBACK_LIST[@]}"; do
    if check_registry_available "$registry" 3; then
      selected_registry="$registry"
      break
    fi
  done
  
  if [ -z "$selected_registry" ]; then
    error "所有 registry 均不可用，请检查网络"
    return 1
  fi
  
  echo "$selected_registry"
}

# 自动选择最优 registry（延迟最低）
select_fastest_registry() {
  local fastest_registry=""
  local min_latency=999999
  
  for registry in "${REGISTRY_FALLBACK_LIST[@]}"; do
    local latency
    latency=$(measure_registry_latency "$registry")
    
    if [ "$latency" -lt "$min_latency" ]; then
      min_latency="$latency"
      fastest_registry="$registry"
    fi
    
    info "registry 延迟: $registry - ${latency}ms"
  done
  
  if [ -n "$fastest_registry" ]; then
    success "选择最快的 registry: $fastest_registry (${min_latency}ms)"
    echo "$fastest_registry"
  else
    error "无法找到可用的 registry"
    return 1
  fi
}

# 带降级的 registry 设置
setup_registry_with_fallback() {
  local pkg_manager="${1:-yarn}"
  local registry
  
  info "开始选择可用的 registry..."
  
  registry=$(select_available_registry)
  
  if [ -z "$registry" ]; then
    error "registry 设置失败"
    return 1
  fi
  
  set_registry "$registry" "$pkg_manager"
}
```

### 私有源不可用时跳过

```bash
# 检测私有源，不可用时使用公共镜像
setup_registry_safe() {
  local private_registry="${1:-${PRIVATE_REGISTRY:-}}"
  local fallback_registry="${2:-https://registry.npmmirror.com}"
  local pkg_manager="${3:-yarn}"
  
  if check_registry_available "$private_registry" 5; then
    info "使用私有源: $private_registry"
    set_registry "$private_registry" "$pkg_manager"
  else
    warn "私有源不可用，降级到公共镜像: $fallback_registry"
    set_registry "$fallback_registry" "$pkg_manager"
  fi
}
```

## 二进制包处理

### node-sass 预编译二进制

**问题**：node-sass 编译失败（Python、node-gyp 依赖）

**解决**：直接下载预编译的 binding.node

```bash
# node-sass 版本与 Node.js 版本对应关系
# Node 12 -> linux-x64-72
# Node 14 -> linux-x64-83
# Node 16 -> linux-x64-93

# 获取 Node.js ABI 版本
get_node_abi_version() {
  node -p "process.versions.modules"
}

# 安装 node-sass 预编译二进制
install_node_sass_binary() {
  local sass_version="${1:-4.14.1}"
  local node_abi
  node_abi=$(get_node_abi_version)
  
  local binding_dir="node_modules/node-sass/vendor/linux-x64-${node_abi}"
  local binding_file="${binding_dir}/binding.node"
  
  if [ -f "$binding_file" ]; then
    info "node-sass 预编译二进制已存在"
    return 0
  fi
  
  info "下载 node-sass v${sass_version} 预编译二进制 (ABI ${node_abi})..."
  mkdir -p "$binding_dir"
  
  local download_url="https://npmmirror.com/mirrors/node-sass/v${sass_version}/linux-x64-${node_abi}_binding.node"
  
  if curl -sL -o "$binding_file" "$download_url"; then
    success "node-sass 预编译完成"
    return 0
  else
    error "下载 node-sass 二进制失败: $download_url"
    return 1
  fi
}

# 自动检测 node-sass 版本并安装
auto_install_node_sass_binary() {
  local pkg_json="package.json"
  
  if [ ! -f "$pkg_json" ]; then
    return 0
  fi
  
  # 从 package.json 提取 node-sass 版本
  local sass_version
  sass_version=$(grep -oP '"node-sass":\s*"\^\K[\d.]+' "$pkg_json" 2>/dev/null | head -1)
  
  if [ -n "$sass_version" ]; then
    info "检测到 node-sass@$sass_version"
    install_node_sass_binary "$sass_version"
  fi
}
```

### sass-embedded（Dart Sass 二进制）

```bash
# sass-embedded 二进制下载
install_sass_embedded_binary() {
  local version="${1:-1.54.0}"
  local platform="linux-x64"
  
  local cache_dir="$HOME/.cache/sass-embedded"
  local binary_path="$cache_dir/sass-embedded-$version-$platform"
  
  if [ -f "$binary_path/dart-sass-embedded" ]; then
    info "sass-embedded 二进制已存在"
    return 0
  fi
  
  info "下载 sass-embedded v${version}..."
  mkdir -p "$cache_dir"
  
  local download_url="https://github.com/sass/dart-sass-embedded/releases/download/${version}/sass_embedded-${version}-${platform}.tar.gz"
  
  curl -sL "$download_url" | tar xz -C "$cache_dir" || {
    error "下载 sass-embedded 失败"
    return 1
  }
  
  success "sass-embedded 安装完成"
}
```

### Electron 预编译二进制

```bash
# Electron 二进制镜像配置
setup_electron_mirror() {
  local mirror_url="${1:-https://npmmirror.com/mirrors/electron/}"
  
  export ELECTRON_MIRROR="$mirror_url"
  export ELECTRON_CUSTOM_DIR="{{ version }}"
  
  info "Electron 镜像: $ELECTRON_MIRROR"
}

# 预下载 Electron（避免 postinstall 超时）
predownload_electron() {
  local electron_version="${1:-13.1.7}"
  local platform="linux"
  local arch="x64"
  
  local cache_dir="$HOME/.cache/electron"
  local zip_file="$cache_dir/electron-v${electron_version}-${platform}-${arch}.zip"
  
  if [ -f "$zip_file" ]; then
    info "Electron 二进制已缓存"
    return 0
  fi
  
  info "预下载 Electron v${electron_version}..."
  mkdir -p "$cache_dir"
  
  local download_url="https://npmmirror.com/mirrors/electron/${electron_version}/electron-v${electron_version}-${platform}-${arch}.zip"
  
  curl -sL -o "$zip_file" "$download_url" || {
    error "下载 Electron 失败"
    return 1
  }
  
  success "Electron 预下载完成"
}
```

### Puppeteer / Chromium 二进制

```bash
# Puppeteer 跳过 Chromium 下载（使用系统 Chrome）
skip_puppeteer_download() {
  export PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
  export PUPPETEER_EXECUTABLE_PATH=/usr/bin/google-chrome
  
  info "Puppeteer 将跳过 Chromium 下载"
}

# Puppeteer 使用国内镜像下载 Chromium
setup_puppeteer_mirror() {
  export PUPPETEER_DOWNLOAD_HOST="https://npmmirror.com/mirrors"
  info "Puppeteer 镜像: $PUPPETEER_DOWNLOAD_HOST"
}
```

## 特定包补丁

### vue-native-websocket 补丁

**问题**：私有源缺失该包，导致安装失败

**解决**：从 npm 官方源单独安装

```bash
# 安装 vue-native-websocket（从 npm 官方源）
patch_vue_native_websocket() {
  local target_dir="node_modules/vue-native-websocket"
  local version="${1:-2.0.15}"
  
  if [ -d "${target_dir}/dist" ]; then
    info "vue-native-websocket 已存在"
    return 0
  fi
  
  info "从 npm 官方源安装 vue-native-websocket@${version}..."
  mkdir -p "$target_dir"
  
  curl -sL "https://registry.npmjs.org/vue-native-websocket/-/vue-native-websocket-${version}.tgz" | \
    tar xz -C "$target_dir" --strip-components=1 || {
    warn "vue-native-websocket 安装失败，可能不影响主功能"
    return 0
  }
  
  success "vue-native-websocket 已安装"
}
```

### @framework/* 私有包兜底

```bash
# 检查私有包是否可访问
check_private_package() {
  local package_name="$1"
  local registry="${2:-${PRIVATE_REGISTRY:-}}"
  
  local package_url="${registry}/${package_name}"
  
  if curl -sf --max-time 5 "$package_url" >/dev/null 2>&1; then
    return 0
  else
    warn "私有包不可访问: $package_name"
    return 1
  fi
}

# 批量检查私有包
verify_private_packages() {
  local private_packages=(
    "@framework/business-ui-pages"
    "@config/eslint-config-app"
  )
  
  local failed_packages=()
  
  for pkg in "${private_packages[@]}"; do
    if ! check_private_package "$pkg"; then
      failed_packages+=("$pkg")
    fi
  done
  
  if [ ${#failed_packages[@]} -gt 0 ]; then
    error "以下私有包不可访问:"
    for pkg in "${failed_packages[@]}"; do
      error "  - $pkg"
    done
    return 1
  fi
  
  success "所有私有包可访问"
}
```

## 依赖安装最佳实践

```bash
# 带重试的依赖安装
install_dependencies_with_retry() {
  local pkg_manager="${1:-yarn}"
  local max_retries="${2:-3}"
  local retry_count=0
  
  while [ $retry_count -lt $max_retries ]; do
    info "安装依赖 (尝试 $((retry_count + 1))/$max_retries)..."
    
    case "$pkg_manager" in
      yarn)
        if yarn install --frozen-lockfile --non-interactive; then
          success "依赖安装成功"
          return 0
        fi
        ;;
      npm)
        if npm ci; then
          success "依赖安装成功"
          return 0
        fi
        ;;
      pnpm)
        if pnpm install --frozen-lockfile; then
          success "依赖安装成功"
          return 0
        fi
        ;;
    esac
    
    retry_count=$((retry_count + 1))
    warn "依赖安装失败，等待 5 秒后重试..."
    sleep 5
  done
  
  error "依赖安装失败（已重试 $max_retries 次）"
  return 1
}

# 完整的依赖安装流程（含预处理）
install_dependencies_full() {
  local pkg_manager="${1:-yarn}"
  
  # 1. 设置 registry
  setup_registry_with_fallback "$pkg_manager"
  
  # 2. 设置二进制包镜像
  export SASS_BINARY_SITE="https://npmmirror.com/mirrors/node-sass"
  export ELECTRON_MIRROR="https://npmmirror.com/mirrors/electron/"
  export PUPPETEER_DOWNLOAD_HOST="https://npmmirror.com/mirrors"
  
  # 3. 预安装 node-sass 二进制
  auto_install_node_sass_binary
  
  # 4. 安装依赖（带重试）
  install_dependencies_with_retry "$pkg_manager" 3
  
  # 5. 补丁特定包
  patch_vue_native_websocket
  
  success "依赖安装完成"
}
```

## Registry 配置生成

```bash
# 生成 .npmrc 文件
generate_npmrc() {
  local project_root="$1"
  local registry="${2:-${PRIVATE_REGISTRY:-}}"
  local npmrc="$project_root/.npmrc"
  
  info "生成 .npmrc: $npmrc"
  
  cat > "$npmrc" <<EOF
# NPM Registry
registry=$registry

# 二进制包镜像
sass_binary_site=https://npmmirror.com/mirrors/node-sass
electron_mirror=https://npmmirror.com/mirrors/electron/
puppeteer_download_host=https://npmmirror.com/mirrors
chromedriver_cdnurl=https://npmmirror.com/mirrors/chromedriver

# 网络配置
fetch-retries=3
fetch-retry-mintimeout=10000
fetch-retry-maxtimeout=60000
EOF
  
  success ".npmrc 已生成"
}

# 生成 .yarnrc 文件（Yarn 1.x）
generate_yarnrc() {
  local project_root="$1"
  local registry="${2:-${PRIVATE_REGISTRY:-}}"
  local yarnrc="$project_root/.yarnrc"
  
  info "生成 .yarnrc: $yarnrc"
  
  cat > "$yarnrc" <<EOF
registry "$registry"
sass_binary_site "https://npmmirror.com/mirrors/node-sass"
electron_mirror "https://npmmirror.com/mirrors/electron/"
puppeteer_download_host "https://npmmirror.com/mirrors"
EOF
  
  success ".yarnrc 已生成"
}
```

## 参考资料

- [npm registry 文档](https://docs.npmjs.com/cli/v7/using-npm/registry)
- [Yarn registry 配置](https://classic.yarnpkg.com/en/docs/cli/config/#toc-yarn-config-set)
- [pnpm registry 配置](https://pnpm.io/npmrc#registry)
- [淘宝 npm 镜像](https://npmmirror.com/)
- [node-sass 二进制下载](https://github.com/sass/node-sass/releases)
- [Verdaccio 私有 npm 仓库](https://verdaccio.org/)
