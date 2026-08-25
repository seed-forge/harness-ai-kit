# Changelog

## 0.1.10 - 2026-08-25

- Public OSS metadata uses the `public` namespace and `seedforge` owner, and source resolution now uses public-registry instead of the retired private registry label.

## 0.1.9 - 2026-08-22

- 新增 Docker daemon 代理验收清单：大小写变量冲突、重复 systemd drop-in、NO_PROXY 覆盖范围，以及 daemon/容器代理层级区分。

## 0.1.8 - 2026-08-20
- 环境值占位符抽取：组织内部集群 IP/域名改为 {<host>_host}/{<host>_host}/{<host>_host}/{base_domain}/{service_domain}/{root_domain} config 占位符（docs/config-governance.md §12）

## 0.1.7 - 2026-08-20
- OSS notice/环境适配声明注入。

## 0.1.6 - 2026-08-14

- frontmatter 规范化：SKILL.md 统一 LF / 无 BOM / 单一 YAML frontmatter 块，修复 AI IDE 加载告警（missing YAML frontmatter delimited by ---）。
## 0.1.5 - 2026-08-06

- 治理清欠：结构合规修复后版本抬升（ref_link、ref_rename:README.md->REFERENCE-README.md、refs）。

## 0.1.4 - 2026-05-24

- 新增 `references/REFERENCE-NEXUS-ECOSYSTEM-PRELOAD.md`（Nexus npm/maven/pypi 预热与 manifest 治理）
- `SKILL.md` / `REFERENCE-MIRROR-RECIPES.md`：交叉引用 artifact-preload 与 L3b 预热决策

## 0.1.3 - 2026-05-20

- `sources.preferred` 改为 registry 优先

## 0.1.2 - 2026-05-22

- L1 proxy: cross-link 组织内部集群 <host>/<host> default Clash endpoints (`REFERENCE-组织内部集群-OUTBOUND-HTTP-PROXY.md`)
- `REFERENCE-MIRROR-RECIPES.md` §11: per-host HTTP_PROXY table

## 0.1.1 - 2026-05-15

- rename `references/mirror-recipes.md` to `references/REFERENCE-MIRROR-RECIPES.md` to satisfy harness-ai-kit reference naming rules
- add this changelog so `skill.json` and `CHANGELOG.md` top versions stay aligned
