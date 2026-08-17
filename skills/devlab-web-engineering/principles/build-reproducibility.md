# 构建可复现性（Web）

- **锁文件强制**：package-lock.json / pnpm-lock.yaml / yarn.lock 必须入库；
  安装用 `npm ci` / `pnpm install --frozen-lockfile`，禁止裸 `npm install` 漂移。
- **版本 pin**：直接依赖固定版本范围；CI 与本地用同一 lockfile。
- **环境一致性**：Node 版本由 .nvmrc / engines 声明；构建命令统一从 scripts/ 入口执行。
- **构建确定性**：禁止构建时依赖网络可变资源（CDN 引用纳入版本管理审查）；
  产物带内容哈希（Vite 默认 assets 哈希）。
- **验证即证据**：每次构建记录产物大小/时间/环境，作为回归基线
  （视觉回归基线走 devlab-web-visual-ops）。
