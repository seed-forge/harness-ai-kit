# Template Skill — Asset Router

> **AI-Kit Router**：本文件是本 Skill 的**内部资产导航**，只列同级目录下的内部资产（references/scripts/templates/examples）。
> 不列外部 skill/CLI/MCP（外部交互见 `SKILL.md` 的 `## Integration Points` 与 `skill.json` 的 `integrations`）。

## 内部资产地图

| 资产 | 路径 | 用途 |
|------|------|------|
| 主文档 | `SKILL.md` | 技能入口、工作流、约束、Integration Points、Human Decisions 汇总 |
| 元数据 | `skill.json` | id/version/dependencies/integrations 等结构化声明 |
| 决策清单 | `decisions.yaml` | Human Decisions 结构化（有决策点时必需） |
| 变更记录 | `CHANGELOG.md` | 版本变更历史 |
| 使用指南 | `USAGE.md` | 安装、前置条件、可复制 Prompt |
| 参考文档 | `references/` | 专题参考；导航见 `references/README.md` |
| 脚本 | `scripts/` | 可自动化固定流程（如有） |
| 模板 | `templates/` | 模板文件（如有） |
| 示例 | `examples/` | 真实使用案例（如有） |

## 使用说明

- 新增 reference 时，在 `references/README.md` 补一行导航。
- 新增可复用脚本时，命名遵循 `<verb>-<target>.{py,sh}`（validate/generate/sync/check）。
- 删除本说明中未实际存在的资产行，保持导航与目录一致。
