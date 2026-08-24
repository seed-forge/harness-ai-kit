# Changelog

## 0.1.7 - 2026-08-24

- Public-release metadata normalization: remove internal-only execution context
  and use the public `skill-registry` source name.

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

- L1 proxy: cross-link Team node1/node2 default Clash endpoints (`REFERENCE-HOMELAB-OUTBOUND-HTTP-PROXY.md`)
- `REFERENCE-MIRROR-RECIPES.md` §11: per-host HTTP_PROXY table

## 0.1.1 - 2026-05-15

- rename `references/mirror-recipes.md` to `references/REFERENCE-MIRROR-RECIPES.md` to satisfy team-ai-kit reference naming rules
- add this changelog so `skill.json` and `CHANGELOG.md` top versions stay aligned
