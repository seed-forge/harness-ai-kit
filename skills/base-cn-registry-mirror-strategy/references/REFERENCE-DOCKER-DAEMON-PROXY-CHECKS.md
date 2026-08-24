# Docker Daemon Proxy Checks

Docker daemon 代理、Compose 容器内代理和 CI 环境变量是三个不同层级，不能用“某处有代理”代替逐层验收。

## 检查清单

1. 读取 systemd Docker service 的 effective environment，确认 `HTTP_PROXY`、`HTTPS_PROXY`、`NO_PROXY`。
2. 同时检查大小写变量；大小写冲突时以 daemon 实际生效值为准并清理歧义。
3. 列出 `docker.service.d/*.conf`，同一 service 只保留一个 canonical proxy drop-in，避免旧 endpoint 与新 endpoint 同时生效。
4. `NO_PROXY` 至少覆盖 loopback、内部域名后缀、Harbor、Gitea、国内 registry 和 GHCR 等无需出站代理的地址。
5. 分别检查 Compose `environment` / `env_file` 与 Docker daemon；容器内变量不能证明宿主机 pull 使用了代理。
6. 修改后执行 daemon reload/restart，再用一次大镜像 pull 和 `RepoDigests` 做真实验证。

## 选择顺序

优先组织 Harbor/registry cache；没有可用 cache 时，使用目标机 Docker daemon 的专线或 Clash HTTP(S) 代理；临时预拉取只作为受控补救，并必须记录 digest。
