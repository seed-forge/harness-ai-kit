# Changelog

## 0.3.6 - 2026-08-22

- 新增 raw hosted 资产退役/清理 reference，覆盖 archive、metadata、checksum、index 与回读验收。

## 0.3.5 - 2026-08-20
- 环境值占位符抽取：组织内部集群 IP/域名改为 {<host>_host}/{<host>_host}/{<host>_host}/{base_domain}/{service_domain}/{root_domain} config 占位符（docs/config-governance.md §12）

## 0.3.4 - 2026-08-14

- frontmatter 规范化：SKILL.md 统一 LF / 无 BOM / 单一 YAML frontmatter 块，修复 AI IDE 加载告警（missing YAML frontmatter delimited by ---）。
## 0.3.3 - 2026-08-06

- 治理清欠：结构合规修复后版本抬升（ref_link、ref_rename:README.md->REFERENCE-README.md、refs）。

## 0.3.2 - 2026-07-26

- 约束段新增 RBAC 角色门禁说明（配套 CLI nexusctl ≥ 0.5.0，场景化三档权限）

## 0.3.0

- **P0 数据正确性**：presets blob_store 自动推导为 `{format}-proxy-store`；repo get 降级到 list 过滤；inventory export 补充 blob_store/write_policy/remote_url 详情
- **P1 UX**：`--json`/`--verbose` 可在子命令后使用；`--format` 添加 metavar 提示；probe 迁移到 SDK
- **P2 功能补全**：新增 `repo update-group`/`update-proxy`/`update-hosted`；`--output fleet-platform` 别名；Profile 配置文件 `~/.nexusctl/profiles.yaml`
- **P3 架构优化**：class_map 动态推导（消除 26 行硬编码）；新增 `blobstore` 子命令组（list/create-file/delete）；新增 `cleanup-policy` 子命令组（list/get）；SDK 版本约束 `>=3.74.1,<4.0`；新增 `inventory diff` 漂移检测
- **P4 文档**：SKILL.md 添加配置上下文段落；新建 config.defaults.yaml；命名规范补充 cleanup policy

## 0.2.2

- Blob store 自动推导（hosted 仓库默认 `{format}-hosted-store`）
- APT 格式支持（`--distribution`、`--flat` 参数）

## 0.2.1

- 修复 SDK host 路径（添加 `/service/rest` 前缀）

## 0.2.0

- 引入 `nexus_api_client` 官方 SDK
- 新增仓库 CRUD：create-proxy/hosted/group、delete、get
- 新增预设模板：create-from-preset、list-presets
- 新增 inventory 导出：export、summary
- 支持格式：pypi, npm, maven2, docker, raw, nuget, go, rubygems, apt

## 0.1.0

- 初始发布：doctor、repo list、probe
