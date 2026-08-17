# Node.js 版本管理参考

## 概述

Node.js 版本管理工具解决多项目版本切换问题。主流工具有 nvm（Shell 脚本，兼容性好）、fnm（Rust 实现，速度快）、volta（透明切换）、asdf（多语言统一管理）。本文档提供统一的检测/切换逻辑，可嵌入到生成的 common.sh 脚本中。

## 版本管理工具对比

| 工具 | 实现语言 | 启动速度 | 配置文件 | 自动切换 | 平台支持 |
|------|---------|---------|---------|---------|---------|
| **nvm** | Shell | 慢（~200ms） | `.nvmrc` | ❌（需钩子） | Linux/macOS/WSL |
| **fnm** | Rust | 快（<10ms） | `.node-version`, `.nvmrc` | ✅ | Linux/macOS/Windows |
| **volta** | Rust | 快（<5ms） | `package.json` engines | ✅（透明） | Linux/macOS/Windows |
| **asdf** | Shell | 中（~50ms） | `.tool-versions` | ✅（插件） | Linux/macOS |

## nvm（Node Version Manager）

### 特征

- **安装**: `curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash`
- **配置文件**: `.nvmrc`
- **命令前缀**: `nvm use`, `nvm install`
- **生态**: 最成熟，社区最大

### 初始化脚本

```bash
# 加载 nvm（必须在使用前执行）
load_nvm() {
  export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
  
  if [ ! -s "$NVM_DIR/nvm.sh" ]; then
    return 1
  fi
  
  # shellcheck source=/dev/null
  \. "$NVM_DIR/nvm.sh" --no-use
  return 0
}
```

### 版本切换逻辑

```bash
use_node_nvm() {
  local target_version="$1"
  
  if ! load_nvm; then
    error "nvm 未安装"
    error "安装命令: curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash"
    return 1
  fi
  
  local current_version
  current_version=$(node -v 2>/dev/null || echo "none")
  
  if [ "$current_version" = "v$target_version" ]; then
    info "Node.js 已是 v$target_version"
    return 0
  fi
  
  info "切换 Node.js 到 v$target_version (当前: $current_version)"
  
  # 检查版本是否已安装
  if ! nvm ls "$target_version" &>/dev/null; then
    warn "Node.js v$target_version 未安装，尝试安装..."
    nvm install "$target_version" || {
      error "安装 Node.js v$target_version 失败"
      return 1
    }
  fi
  
  nvm use "$target_version" || {
    error "切换到 Node.js v$target_version 失败"
    return 1
  }
  
  success "Node.js $(node -v)"
}
```

### .nvmrc 文件自动检测

```bash
# 从 .nvmrc 读取版本
read_nvmrc() {
  local project_root="$1"
  local nvmrc="$project_root/.nvmrc"
  
  if [ -f "$nvmrc" ]; then
    cat "$nvmrc" | tr -d '[:space:]'
  fi
}

# 自动使用 .nvmrc 版本
auto_use_nvmrc() {
  local project_root="$1"
  local nvmrc_version
  
  nvmrc_version=$(read_nvmrc "$project_root")
  
  if [ -n "$nvmrc_version" ]; then
    info "检测到 .nvmrc: $nvmrc_version"
    use_node_nvm "$nvmrc_version"
  else
    warn "未找到 .nvmrc，使用默认版本"
  fi
}
```

### nvm 性能优化（延迟加载）

```bash
# 延迟加载 nvm（提升 shell 启动速度）
lazy_load_nvm() {
  export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
  
  # 仅设置路径，不加载完整脚本
  if [ -s "$NVM_DIR/nvm.sh" ]; then
    export PATH="$NVM_DIR/versions/node/$(cat $NVM_DIR/alias/default 2>/dev/null || echo 'v14.0.0')/bin:$PATH"
  fi
}
```

## fnm（Fast Node Manager）

### 特征

- **安装**: `curl -fsSL https://fnm.vercel.app/install | bash`
- **配置文件**: `.node-version`, `.nvmrc`
- **自动切换**: 支持（cd 时自动触发）
- **速度**: 极快（Rust 实现）

### 初始化脚本

```bash
load_fnm() {
  if ! command -v fnm &>/dev/null; then
    return 1
  fi
  
  # 初始化 fnm 环境
  eval "$(fnm env --use-on-cd)"
  return 0
}
```

### 版本切换逻辑

```bash
use_node_fnm() {
  local target_version="$1"
  
  if ! command -v fnm &>/dev/null; then
    error "fnm 未安装"
    error "安装命令: curl -fsSL https://fnm.vercel.app/install | bash"
    return 1
  fi
  
  local current_version
  current_version=$(node -v 2>/dev/null || echo "none")
  
  if [ "$current_version" = "v$target_version" ]; then
    info "Node.js 已是 v$target_version"
    return 0
  fi
  
  info "切换 Node.js 到 v$target_version (当前: $current_version)"
  
  # 检查版本是否已安装
  if ! fnm list | grep -q "$target_version"; then
    warn "Node.js v$target_version 未安装，尝试安装..."
    fnm install "$target_version" || {
      error "安装 Node.js v$target_version 失败"
      return 1
    }
  fi
  
  fnm use "$target_version" || {
    error "切换到 Node.js v$target_version 失败"
    return 1
  }
  
  success "Node.js $(node -v)"
}
```

### .node-version 文件支持

```bash
# 从 .node-version 读取版本
read_node_version() {
  local project_root="$1"
  local node_version_file="$project_root/.node-version"
  
  if [ -f "$node_version_file" ]; then
    cat "$node_version_file" | tr -d '[:space:]'
  fi
}

# 自动使用 .node-version 版本
auto_use_node_version() {
  local project_root="$1"
  local node_version
  
  node_version=$(read_node_version "$project_root")
  
  if [ -n "$node_version" ]; then
    info "检测到 .node-version: $node_version"
    use_node_fnm "$node_version"
  fi
}
```

### fnm 自动切换钩子

```bash
# 在 .bashrc/.zshrc 中添加（供参考）
eval "$(fnm env --use-on-cd)"

# 手动触发（用于脚本中）
fnm_auto_switch() {
  local project_root="$1"
  cd "$project_root" && fnm use
}
```

## volta

### 特征

- **安装**: `curl https://get.volta.sh | bash`
- **配置文件**: `package.json` 的 `engines` 字段
- **自动切换**: 透明（无感知）
- **适用**: 团队协作（版本锁定在 package.json）

### 初始化脚本

```bash
load_volta() {
  if ! command -v volta &>/dev/null; then
    return 1
  fi
  
  export VOLTA_HOME="${VOLTA_HOME:-$HOME/.volta}"
  export PATH="$VOLTA_HOME/bin:$PATH"
  return 0
}
```

### 版本切换逻辑

```bash
use_node_volta() {
  local target_version="$1"
  
  if ! command -v volta &>/dev/null; then
    error "volta 未安装"
    error "安装命令: curl https://get.volta.sh | bash"
    return 1
  fi
  
  info "使用 volta 安装 Node.js v$target_version"
  
  volta install "node@$target_version" || {
    error "安装 Node.js v$target_version 失败"
    return 1
  }
  
  success "Node.js $(node -v)"
}
```

### package.json engines 字段支持

```bash
# 从 package.json 读取 engines.node
read_package_engines() {
  local project_root="$1"
  local pkg_json="$project_root/package.json"
  
  if [ -f "$pkg_json" ]; then
    grep -oP '"node":\s*"\K[^"]+' "$pkg_json" 2>/dev/null
  fi
}

# 解析版本范围（如 ">=12.0.0" -> "12.0.0"）
parse_node_version_range() {
  local range="$1"
  echo "$range" | sed -E 's/[^0-9.]//g'
}

# volta 自动使用 package.json 版本
auto_use_volta() {
  local project_root="$1"
  local engines_node
  
  engines_node=$(read_package_engines "$project_root")
  
  if [ -n "$engines_node" ]; then
    local version
    version=$(parse_node_version_range "$engines_node")
    info "检测到 package.json engines.node: $engines_node"
    use_node_volta "$version"
  fi
}
```

### volta pin（锁定项目版本）

```bash
# 锁定当前项目的 Node.js 版本（修改 package.json）
volta_pin_version() {
  local target_version="$1"
  
  info "锁定项目 Node.js 版本到 v$target_version"
  volta pin "node@$target_version"
  success "已锁定版本，团队成员将自动使用 v$target_version"
}
```

## asdf

### 特征

- **安装**: `git clone https://github.com/asdf-vm/asdf.git ~/.asdf --branch v0.10.0`
- **配置文件**: `.tool-versions`
- **多语言**: 统一管理 Node.js、Python、Ruby、Java 等
- **插件系统**: `asdf plugin add nodejs`

### 初始化脚本

```bash
load_asdf() {
  export ASDF_DIR="${ASDF_DIR:-$HOME/.asdf}"
  
  if [ ! -s "$ASDF_DIR/asdf.sh" ]; then
    return 1
  fi
  
  # shellcheck source=/dev/null
  \. "$ASDF_DIR/asdf.sh"
  return 0
}
```

### 版本切换逻辑

```bash
use_node_asdf() {
  local target_version="$1"
  
  if ! load_asdf; then
    error "asdf 未安装"
    error "安装命令: git clone https://github.com/asdf-vm/asdf.git ~/.asdf --branch v0.10.0"
    return 1
  fi
  
  # 检查 nodejs 插件是否已安装
  if ! asdf plugin list | grep -q nodejs; then
    warn "asdf nodejs 插件未安装，尝试安装..."
    asdf plugin add nodejs
  fi
  
  info "切换 Node.js 到 v$target_version"
  
  # 检查版本是否已安装
  if ! asdf list nodejs | grep -q "$target_version"; then
    warn "Node.js v$target_version 未安装，尝试安装..."
    asdf install nodejs "$target_version" || {
      error "安装 Node.js v$target_version 失败"
      return 1
    }
  fi
  
  asdf global nodejs "$target_version" || {
    error "切换到 Node.js v$target_version 失败"
    return 1
  }
  
  success "Node.js $(node -v)"
}
```

### .tool-versions 文件支持

```bash
# 从 .tool-versions 读取 nodejs 版本
read_tool_versions() {
  local project_root="$1"
  local tool_versions="$project_root/.tool-versions"
  
  if [ -f "$tool_versions" ]; then
    grep -oP 'nodejs\s+\K[\d.]+' "$tool_versions" 2>/dev/null
  fi
}

# 自动使用 .tool-versions 版本
auto_use_asdf() {
  local project_root="$1"
  
  # asdf 会自动读取 .tool-versions，无需手动切换
  if [ -f "$project_root/.tool-versions" ]; then
    info "检测到 .tool-versions，asdf 将自动切换版本"
    cd "$project_root" || return
  fi
}
```

## 统一版本管理器检测与切换

```bash
# 检测系统中已安装的版本管理器（按优先级）
detect_node_version_manager() {
  if command -v volta &>/dev/null; then
    echo "volta"
  elif command -v fnm &>/dev/null; then
    echo "fnm"
  elif [ -s "$HOME/.nvm/nvm.sh" ]; then
    echo "nvm"
  elif command -v asdf &>/dev/null && asdf plugin list | grep -q nodejs; then
    echo "asdf"
  else
    echo "none"
  fi
}

# 统一的 Node.js 版本切换函数
use_node() {
  local target_version="$1"
  local manager
  
  manager=$(detect_node_version_manager)
  
  case "$manager" in
    volta)
      use_node_volta "$target_version"
      ;;
    fnm)
      use_node_fnm "$target_version"
      ;;
    nvm)
      use_node_nvm "$target_version"
      ;;
    asdf)
      use_node_asdf "$target_version"
      ;;
    none)
      error "未检测到 Node.js 版本管理器"
      error "推荐安装: fnm (快速) 或 nvm (兼容性好)"
      error "  fnm: curl -fsSL https://fnm.vercel.app/install | bash"
      error "  nvm: curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash"
      return 1
      ;;
  esac
}

# 自动检测项目配置文件并切换版本
auto_use_node() {
  local project_root="$1"
  local version
  
  # 优先级: .nvmrc > .node-version > package.json engines > 默认版本
  if [ -f "$project_root/.nvmrc" ]; then
    version=$(read_nvmrc "$project_root")
    info "使用 .nvmrc 中的版本: $version"
  elif [ -f "$project_root/.node-version" ]; then
    version=$(read_node_version "$project_root")
    info "使用 .node-version 中的版本: $version"
  elif [ -f "$project_root/.tool-versions" ]; then
    version=$(read_tool_versions "$project_root")
    info "使用 .tool-versions 中的版本: $version"
  elif [ -f "$project_root/package.json" ]; then
    version=$(read_package_engines "$project_root")
    if [ -n "$version" ]; then
      version=$(parse_node_version_range "$version")
      info "使用 package.json engines 中的版本: $version"
    fi
  fi
  
  if [ -n "$version" ]; then
    use_node "$version"
  else
    warn "未找到版本配置文件，使用系统默认 Node.js"
  fi
}
```

## 版本不匹配时的自动修复

```bash
# 检查当前 Node.js 版本是否匹配项目要求
check_node_version_match() {
  local project_root="$1"
  local required_version
  
  required_version=$(auto_use_node "$project_root")
  
  local current_version
  current_version=$(node -v | sed 's/v//')
  
  if [ "$current_version" != "$required_version" ]; then
    warn "Node.js 版本不匹配"
    warn "  当前版本: $current_version"
    warn "  要求版本: $required_version"
    return 1
  fi
  
  return 0
}

# 强制修复版本不匹配（自动安装缺失版本）
fix_node_version() {
  local project_root="$1"
  
  if ! check_node_version_match "$project_root"; then
    info "自动修复 Node.js 版本..."
    auto_use_node "$project_root"
  fi
}
```

## CI/CD 环境适配

```bash
# CI 环境检测（GitHub Actions、GitLab CI、Jenkins 等）
is_ci_environment() {
  [ -n "${CI:-}" ] || [ -n "${GITHUB_ACTIONS:-}" ] || [ -n "${GITLAB_CI:-}" ]
}

# CI 环境下的 Node.js 版本切换（跳过版本管理器）
use_node_in_ci() {
  local target_version="$1"
  
  if is_ci_environment; then
    # CI 环境通常已安装指定版本，直接使用
    local current_version
    current_version=$(node -v | sed 's/v//')
    
    if [ "$current_version" = "$target_version" ]; then
      info "CI 环境 Node.js 版本已匹配: v$target_version"
      return 0
    else
      warn "CI 环境 Node.js 版本不匹配"
      warn "  当前: v$current_version"
      warn "  要求: v$target_version"
      warn "  请在 CI 配置中指定正确的 Node.js 版本"
      return 1
    fi
  else
    use_node "$target_version"
  fi
}
```

## 参考资料

- [nvm 官方仓库](https://github.com/nvm-sh/nvm)
- [fnm 官方文档](https://github.com/Schniz/fnm)
- [volta 官方文档](https://volta.sh/)
- [asdf 官方文档](https://asdf-vm.com/)
- [Node.js 版本发布计划](https://nodejs.org/en/about/releases/)
