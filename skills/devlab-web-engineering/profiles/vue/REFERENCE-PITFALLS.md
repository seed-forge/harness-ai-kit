# Reference: Web 前端开发踩坑案例库

本文档记录 Web 前端本地开发生命周期脚本中的高频踩坑案例，按 **S-F-W-R-L** 格式组织（Symptom 症状 → Failure 失败现象 → Why 根本原因 → Resolution 解决方案 → Lesson 经验教训）。

---

## 案例 1: pnpm workspace 符号链接在 CI 中失效

### Symptom (症状)

本地开发时 monorepo 子包之间的依赖引用正常，推送到 CI 后构建失败：

```
[ERROR] Cannot find module '@myorg/common'
```

### Failure (失败现象)

- 本地 `pnpm dev` 运行正常
- CI 构建日志显示 `node_modules/@myorg/common` 是一个损坏的符号链接
- Docker 容器内 `ls -la node_modules/@myorg/common` 显示 `No such file or directory`

### Why (根本原因)

pnpm workspace 使用符号链接（symlink）将子包链接到 node_modules，但：

1. **Docker COPY 默认跟随符号链接**：复制符号链接本身而非目标文件，目标路径在容器外
2. **CI 缓存不保留符号链接**：某些 CI 工具（如 Jenkins）缓存 node_modules 时会丢失符号链接元数据
3. **权限问题**：某些文件系统（如 Windows + WSL2）不支持 Unix 符号链接

### Resolution (解决方案)

**方案 A: Dockerfile 强制复制目标文件**

```dockerfile
# 错误写法（默认）
COPY package.json yarn.lock ./
COPY node_modules ./node_modules/

# 正确写法
COPY --from=builder /app/packages/my-app/dist ./dist
# 不复制 node_modules，而是在容器内重新安装
RUN npm ci --production
```

**方案 B: 使用 pnpm deploy（推荐）**

```bash
# 将 workspace 依赖打包成独立目录
pnpm deploy --filter=my-app --prod /app/deploy
```

**方案 C: CI 缓存策略调整**

```yaml
# .github/workflows/build.yml
- uses: actions/cache@v3
  with:
    path: |
      **/node_modules
      ~/.pnpm-store
    key: ${{ runner.os }}-pnpm-${{ hashFiles('**/pnpm-lock.yaml') }}
    # 禁用符号链接缓存
    enableCrossOsArchive: false
```

### Lesson (经验教训)

- **开发脚本应支持 `--bundle` 模式**：打包时自动将 workspace 依赖复制到 node_modules（而非符号链接）
- **CI Dockerfile 优先使用 multi-stage build**：只复制最终产物，不复制 node_modules
- **本地测试 Docker 构建**：`docker build .` 应能在本地复现 CI 问题

---

## 案例 2: .env.local 泄漏到 Git 仓库

### Symptom (症状)

团队成员抱怨本地开发时连接的是别人的数据库/API 端点，修改 `.env.local` 后提交代码，导致其他人的环境配置被覆盖。

### Failure (失败现象)

- `.env.local` 被提交到 Git 仓库
- 包含敏感信息（API Key、数据库密码、私有 IP）
- 多人协作时频繁产生冲突

### Why (根本原因)

1. **`.gitignore` 规则缺失或被覆盖**：
   - 初始化项目时未添加 `.env.local` 到 `.gitignore`
   - 使用 `git add .` 时误添加
2. **命名混淆**：
   - `.env`（模板文件，应提交）vs `.env.local`（个人配置，不应提交）
   - 某些框架默认加载顺序导致 `.env.local` 优先级高于 `.env`
3. **团队规范缺失**：
   - 未提供 `.env.local.example` 模板
   - README 未说明本地配置流程

### Resolution (解决方案)

**1. 修复 `.gitignore`**

```bash
# 添加到 .gitignore
.env.local
.env.*.local
.env.development.local
.env.production.local
```

**2. 移除已提交的敏感文件**

```bash
# 从 Git 历史中删除（需谨慎！）
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .env.local" \
  --prune-empty --tag-name-filter cat -- --all

# 或使用 BFG Repo-Cleaner（更快）
bfg --delete-files .env.local
```

**3. 生成脚本应自动创建模板**

```bash
# devlab-web-bootstrap 生成逻辑
cat > .env.local.example << 'EOF'
# ── 本地开发环境配置模板 ──
# 复制到 .env.local 后修改
VUE_APP_API_BASE_URL=http://localhost:8080
VUE_APP_DEBUG_MODE=true
VUE_APP_PORT=3000
EOF
```

**4. 生命周期脚本应检测 `.env.local` 权限**

```bash
# common.sh 中添加
check_env_file_permissions() {
  local env_file="${1:-.env.local}"
  if [[ -f "$env_file" ]]; then
    local perms=$(stat -c %a "$env_file" 2>/dev/null || stat -f %A "$env_file")
    if [[ "$perms" != "600" ]]; then
      log_warn ".env.local 权限过松（当前: $perms），建议 600"
      log_info "修复: chmod 600 .env.local"
    fi
  fi
}
```

### Lesson (经验教训)

- **生命周期脚本生成时自动配置 `.gitignore`**
- **提供 `.env.local.example` 模板，README 明确说明复制流程**
- **CI/CD 检查 `.env.local` 是否被误提交**（pre-commit hook）

---

## 案例 3: 多包构建顺序依赖导致编译失败

### Symptom (症状)

Monorepo 中构建 `app-main` 时报错：

```
[ERROR] Module not found: Error: Can't resolve '@emas/common' in 'src/utils'
```

但 `@emas/common` 确实存在于 `packages/emas-common`。

### Failure (失败现象)

- 首次克隆仓库后直接运行 `yarn build` 失败
- 手动先 `cd packages/emas-common && yarn build`，再构建 `app-main` 成功
- CI 构建随机失败（并行构建时顺序不确定）

### Why (根本原因)

1. **依赖包未构建**：`@emas/common` 的 `dist/` 目录不存在，但 `app-main` 的 `package.json` 引用了 `@emas/common`
2. **构建工具顺序问题**：
   - Yarn Workspaces 不保证构建顺序（需手动用 Lerna/Nx 管理）
   - `package.json` 的 `scripts` 中未定义依赖关系
3. **缓存失效**：某些构建工具（如 Webpack）缓存了 `node_modules` 的元数据，未检测到子包重新构建

### Resolution (解决方案)

**方案 A: 使用 Lerna 管理构建顺序**

```json
{
  "scripts": {
    "build": "lerna run build --stream --concurrency=1"
  }
}
```

**方案 B: 在生命周期脚本中显式管理顺序**

```bash
# build.sh
build_order=("emas-common" "emas-components" "emas-subapp-integration")

for pkg in "${build_order[@]}"; do
  log_step "构建 $pkg..."
  (cd "packages/$pkg" && npm run build)
done
```

**方案 C: 使用 Turborepo（现代方案）**

```json
{
  "pipeline": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": ["dist/**"]
    }
  }
}
```

**方案 D: 增量构建检查**

```bash
# common.sh 中添加
need_rebuild() {
  local pkg_dir="$1"
  local dist_dir="${pkg_dir}/dist"
  local src_dir="${pkg_dir}/src"

  # 如果 dist/ 不存在，需要构建
  [[ ! -d "$dist_dir" ]] && return 0

  # 比较 src/ 和 dist/ 的最新修改时间
  local src_mtime=$(find "$src_dir" -type f -printf '%T@\n' 2>/dev/null | sort -rn | head -1 | cut -d. -f1)
  local dist_mtime=$(stat -c %Y "$dist_dir" 2>/dev/null || echo 0)

  [[ "${src_mtime:-0}" -gt "$dist_mtime" ]] && return 0
  return 1
}
```

### Lesson (经验教训)

- **生命周期脚本应自动检测依赖构建顺序**（通过 `package.json` 的 `dependencies` 字段）
- **构建脚本应支持 `--force` 参数跳过增量检查**
- **CI 构建应始终 clean build**（避免缓存问题）

---

## 案例 4: 端口冲突（多开发者/多实例）

### Symptom (症状)

启动开发服务器时报错：

```
Error: listen EADDRINUSE: address already in use :::3000
```

或成功启动但无法访问（实际访问到了另一个开发者的服务）。

### Failure (失败现象)

- 多人共用开发服务器时，端口被其他人占用
- 本地启动多个项目时忘记停止旧服务
- 进程崩溃后 PID 文件残留，端口未释放

### Why (根本原因)

1. **硬编码端口**：所有开发者使用同一个端口（如 3000）
2. **PID 文件未清理**：进程被 `kill -9` 强制终止后，PID 文件残留但进程已不存在
3. **端口检测不准确**：脚本只检查 PID 文件，未检查端口实际占用情况
4. **多租户环境缺少命名空间隔离**：如 VDI 多用户共享 IP，端口全局冲突

### Resolution (解决方案)

**1. 动态端口分配（推荐）**

```bash
# common.sh
find_free_port() {
  local base_port="${1:-3000}"
  local max_attempts=100

  for ((i=0; i<max_attempts; i++)); do
    local port=$((base_port + i))
    if check_port "$port"; then
      echo "$port"
      return 0
    fi
  done

  log_error "未找到可用端口（尝试了 ${base_port}-$((base_port + max_attempts - 1))）"
  return 1
}

# dev.sh
PORT=$(find_free_port "${DEFAULT_PORT}")
```

**2. 用户级端口偏移**

```bash
# .env.local.example
# 端口偏移量（根据用户名自动计算，避免冲突）
USER_OFFSET=$(echo "$USER" | md5sum | cut -c1-2 | xargs printf "%d")
PORT=$((3000 + USER_OFFSET))
```

**3. 强制清理残留端口**

```bash
# stop.sh
cleanup_port() {
  local port="$1"
  local pids=$(lsof -t -i :$port 2>/dev/null || true)

  if [[ -n "$pids" ]]; then
    log_warn "清理端口 $port 上的残留进程: $pids"
    echo "$pids" | xargs kill -9 2>/dev/null || true
    sleep 1
  fi
}

# 启动前清理
cleanup_port "$PORT"
```

**4. 健壮的端口检测**

```bash
# common.sh
check_port() {
  local port="$1"

  # 方法 1: lsof（优先）
  if command -v lsof &> /dev/null; then
    lsof -ti:$port >/dev/null 2>&1 && return 1 || return 0
  fi

  # 方法 2: ss（次优）
  if command -v ss &> /dev/null; then
    ss -tlnp 2>/dev/null | grep -q ":$port " && return 1 || return 0
  fi

  # 方法 3: netstat（兼容）
  if command -v netstat &> /dev/null; then
    netstat -tuln 2>/dev/null | grep -q ":$port " && return 1 || return 0
  fi

  # 方法 4: nc 探测（最后手段）
  if command -v nc &> /dev/null; then
    nc -z localhost "$port" 2>/dev/null && return 1 || return 0
  fi

  # 无工具可用，假设端口可用
  return 0
}
```

### Lesson (经验教训)

- **生命周期脚本应支持动态端口分配**
- **启动前必须检测端口实际占用（不只看 PID 文件）**
- **提供 `cleanup` 子命令清理残留资源**

---

## 案例 5: node_modules 缓存导致构建异常

### Symptom (症状)

修改代码后构建/热更新不生效，或出现奇怪的错误：

```
[ERROR] TypeError: Cannot read property 'xxx' of undefined
```

删除 `node_modules` 重新安装后问题消失。

### Failure (失败现象)

- 修改 `package.json` 的依赖版本后未重新安装
- Webpack/Vite 缓存了旧的模块元数据
- pnpm/yarn 的 store/cache 损坏
- monorepo 中子包的 `node_modules` 与根目录不同步

### Why (根本原因)

1. **依赖版本不一致**：
   - `package.json` 改了但 `lock` 文件未更新
   - CI 缓存了旧的 `node_modules`
2. **构建工具缓存**：
   - Webpack 的 `.cache/` 目录
   - Vite 的 `node_modules/.vite/`
   - Babel 的 `.babel-cache/`
3. **包管理器缓存**：
   - pnpm 的 `~/.pnpm-store` 全局缓存损坏
   - Yarn 的 `~/.yarn/cache`
4. **子包符号链接失效**：
   - Monorepo 中修改了 `common` 包但未重新 link

### Resolution (解决方案)

**1. 清理脚本（devlab-web-bootstrap 应生成）**

```bash
# clean.sh
clean_all() {
  log_step "清理构建缓存..."

  # 删除构建产物
  rm -rf dist/ build/ out/

  # 删除构建工具缓存
  rm -rf .cache/ node_modules/.cache/ node_modules/.vite/

  # 删除 Babel 缓存
  rm -rf node_modules/.babel-cache/

  # 清理 Webpack 缓存（Vue CLI）
  rm -rf node_modules/.cache/babel-loader/
  rm -rf node_modules/.cache/vue-loader/

  # 清理 Next.js 缓存
  rm -rf .next/

  log_success "缓存已清理"
}

clean_deep() {
  log_warn "将删除 node_modules，需重新安装（Y/n）"
  read -r confirm
  [[ ! "$confirm" =~ ^[Yy]?$ ]] && return 0

  clean_all

  # 删除 node_modules
  log_step "删除 node_modules..."
  rm -rf node_modules/
  rm -rf packages/*/node_modules/

  # 清理包管理器缓存（可选）
  if command -v pnpm &> /dev/null; then
    pnpm store prune
  fi

  if command -v yarn &> /dev/null; then
    yarn cache clean
  fi

  log_success "node_modules 已删除，运行 install.sh 重新安装"
}
```

**2. 增量安装检测**

```bash
# common.sh
need_reinstall() {
  local lockfile="yarn.lock"  # 或 package-lock.json / pnpm-lock.yaml

  # 如果 node_modules 不存在，需要安装
  [[ ! -d "node_modules" ]] && return 0

  # 如果 lockfile 不存在，需要安装
  [[ ! -f "$lockfile" ]] && return 0

  # 比较 lockfile 和 node_modules 的修改时间
  local lock_mtime=$(stat -c %Y "$lockfile" 2>/dev/null || stat -f %m "$lockfile")
  local nm_mtime=$(stat -c %Y "node_modules" 2>/dev/null || stat -f %m "node_modules")

  [[ "$lock_mtime" -gt "$nm_mtime" ]] && return 0
  return 1
}

# dev.sh 启动前检查
if need_reinstall; then
  log_warn "依赖已过期，需重新安装"
  bash scripts/frontend/install.sh
fi
```

**3. 构建前自动清理缓存**

```bash
# build.sh
if [[ "${CLEAN_CACHE:-false}" == "true" ]]; then
  log_step "清理缓存..."
  rm -rf node_modules/.cache/ .cache/
fi
```

### Lesson (经验教训)

- **生命周期脚本应提供 `clean` 和 `clean-deep` 两个清理级别**
- **构建脚本支持 `--clean` 参数**
- **启动脚本自动检测 `lock` 文件变化并提示重新安装**
- **CI 构建应缓存 `~/.pnpm-store` 而非 `node_modules`（更可靠）**

---

## 总结

| 案例 | 核心教训 | 对应脚本函数 |
|------|---------|------------|
| 1. pnpm 符号链接失效 | 生命周期脚本应支持 `--bundle` 模式打包 workspace 依赖 | `bundle_workspace_deps()` |
| 2. .env.local 泄漏 | 自动生成 `.env.local.example` + 权限检查 | `check_env_file_permissions()` |
| 3. 多包构建顺序 | 自动检测依赖拓扑排序 + 增量构建 | `build_in_order()`, `need_rebuild()` |
| 4. 端口冲突 | 动态端口分配 + 强制清理 | `find_free_port()`, `cleanup_port()` |
| 5. node_modules 缓存 | 提供 `clean` / `clean-deep` 清理级别 | `clean_all()`, `clean_deep()` |

这些案例应作为 **devlab-web-bootstrap** 技能生成脚本时的设计依据。
