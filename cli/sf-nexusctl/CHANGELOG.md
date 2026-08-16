# Changelog

## 0.5.2 - 2026-08-15

- 修复：配置读取链路接入统一配置链（`~/.harness-ai-kit/config.yaml` → `assets.nexusctl`）。
  此前 `resolve_config` 只读 CLI 参数 / `NEXUS_*` 环境变量 / `~/.nexusctl/profiles.yaml`，
  写入全局配置的 `nexus_base_url`/`user`/`password` 完全不生效。
  优先级：CLI 参数 > 统一链（config.yaml > 环境变量 > .env.tak > defaults）> legacy profile。
- 兼容：`assets.nexusctl` 中旧键 `nexus_base_url` 作为 `base_url` 别名继续可用。
- `config.defaults.yaml` 声明 `base_url`/`user`/`password` 键（含 env_var、sensitivity）。

## 0.5.1 - 2026-08-06

- 治理清欠：结构合规修复后版本抬升（usage_missing）。

## [0.5.0] - 2026-07-26

### Added

- 制品仓库场景 RBAC：repo create-*=contributor；update-*/delete/blobstore/user=maintainer；create-readonly=contributor

