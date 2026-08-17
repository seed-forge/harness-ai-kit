# DevLab Web Visual Ops — Asset Router

> **AI-Kit Router**：本文件是本 Skill 的 *内部资产导航*，只列同级目录下的内部资产（references/scripts/templates/examples）。
> 不列外部 skill/CLI/MCP（外部交互见 `SKILL.md` 的 `## Integration Points` 与 `skill.json` 的 `integrations`）。

## 内部资产地图

| 资产 | 路径 | 用途 |
|------|------|------|
| 主文档 | `SKILL.md` | 技能入口、三层架构、Router 规则、约束、Integration Points、Human Decisions 汇总 |
| 元数据 | `skill.json` | id/version/dependencies/integrations 等结构化声明 |
| 决策清单 | `decisions.yaml` | Human Decisions 结构化（HD-1..HD-5） |
| 变更记录 | `CHANGELOG.md` | 版本变更历史 |
| 使用指南 | `USAGE.md` | 安装、前置条件、可复制 Prompt |
| 配置默认值 | `config.defaults.yaml` | 运行时配置项声明（key/type/required/sensitivity） |
| 参考文档 | `references/REFERENCE-ROUTER-ADAPTERS.md` | Router 四类执行器操作细则 |
| 参考文档 | `references/REFERENCE-WORKFLOWS.md` | 五类 Workflow 步骤细则 |
| 导航索引 | `references/REFERENCE-INDEX.md` | 专题文档导航 |

## 使用说明

- 新增 reference 时，在 `references/REFERENCE-INDEX.md` 补一行导航。
- 新增可复用脚本时，命名遵循 `<verb>-<target>.{py,sh}`（validate/generate/sync/check）。
- 删除本说明中未实际存在的资产行，保持导航与目录一致。
