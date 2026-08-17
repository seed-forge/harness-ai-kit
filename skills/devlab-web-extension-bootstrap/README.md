# DevLab Web Extension Bootstrap — Asset Router

> **AI-Kit Router**：本文件是本 Skill 的**内部资产导航**，只列同级目录下的内部资产。
> 外部交互见 `SKILL.md` 的 `## Integration Points` 与 `skill.json` 的 `integrations`。

## 内部资产地图

| 资产 | 路径 | 用途 |
|------|------|------|
| 主文档 | `SKILL.md` | 技能入口、五阶段工作流、约束、Integration Points、Human Decisions |
| 元数据 | `skill.json` | id/version/tags/integrations/environment 结构化声明 |
| 决策清单 | `decisions.yaml` | Human Decisions 结构化（HD-1 通道优先级、HD-2 浏览器与框架） |
| 变更记录 | `CHANGELOG.md` | 版本变更历史 |
| 使用指南 | `USAGE.md` | 前置条件、可直接复制的中文 Prompt |
| 参考文档 | `references/REFERENCE-DETECTION-AND-E2E.md` | 检测器骨架、wxt.config 基线、mock+CfT e2e harness、合规清单 |

## 使用说明

- 新增 reference（`REFERENCE-*.md`）后，在 `SKILL.md` 的「专题引用」补一行（校验器要求每个 REFERENCE 文件都被 SKILL.md 提及）。
- 本技能是方法论；站点特定常量（host/路径正则/字段名）留给具体项目替换。
