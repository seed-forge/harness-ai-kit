# devlab-web-context — Asset Router

> **AI-Kit Router**：本文件是本 Skill 的**内部资产导航**，只列同级目录下的内部资产。
> 不列外部 skill/CLI/MCP（外部交互见 `SKILL.md` 的 `## Integration Points` 与 `skill.json` 的 `integrations`）。

## 内部资产地图

| 资产 | 路径 | 用途 |
|------|------|------|
| 主文档 | `SKILL.md` | 双模式入口（模式 A 规则包 / 模式 B 完整工作流）、四原则摘要、画像契约、HD 决策 |
| 元数据 | `skill.json` | id/version/dependencies/integrations 结构化声明 |
| 决策清单 | `decisions.yaml` | HD-W1 子类型判定 / HD-W2 脱敏 / HD-W3 台账委托 |
| 变更记录 | `CHANGELOG.md` | 版本变更历史 |
| 使用指南 | `USAGE.md` | 前置条件、模式 A/B 可复制 Prompt、验证清单、常见失败 |
| 子类型 profile | `profiles/vue-microfrontend.md` | Vue2 微前端实证级信号与特有条目 |
| 子类型 profile | `profiles/react-spa.md` | React SPA 骨架（模板级，待实战回填） |
| 通用规则 | `references/REFERENCE-WEB-RULES.md` | 跨子类型通用 web 信号与扫描方法、敏感信息边界 |
| 画像示例 | `examples/vue-microfrontend-project.md` | 契约格式样例（脱敏） |

## 家族化说明

`devlab-web-context` 是 `<domain>-context` 家族首个成员。后续成员（`devlab-srv-context` / `devlab-infra-context` / `devlab-tool-context`）同构：
- 共享 `devlab-context-bootstrap` 通用层（四原则全文 + 社区引用 + 五件套骨架）。
- 各自只承载领域规则：`SKILL.md`（双模式入口 + 四原则摘要）+ `profiles/`（子类型）+ `references/`（通用规则）+ `examples/`。

## 使用说明

- 新增前端子类型：新建 `profiles/<type>.md`（参照 react-spa 骨架），在 `SKILL.md` 模式 A 步骤 1 的判定表加信号行。
- 通用 web 信号有更新：改 `references/REFERENCE-WEB-RULES.md`（所有子类型共享）。
- 画像契约变更：必须同步 `SKILL.md` 契约段 + `examples/` 示例 + bootstrap 的消费逻辑。
