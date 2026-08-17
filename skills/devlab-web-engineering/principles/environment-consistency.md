# 环境一致性（Web）

- **Node 版本统一**：.nvmrc + engines 双声明；use_node() 自动切换（nvm/fnm/volta）。
- **环境变量分层**：.env.local（个人，gitignore）+ .env.development（团队共享）+
  .env.production（构建期）；框架前缀规范（VITE_ / VUE_APP_ / NEXT_PUBLIC_）。
- **端口协调**：多开发者/多子包固定端口映射表；check_port + kill_port 防冲突
  （区分自己的旧进程直接杀 vs 他人进程需确认）。
- **registry 一致**：团队统一私有源 + 官方源降级策略（setup_registry）。
- **doctor 巡检**：doctor.sh 10 项检查作为环境健康基线。
