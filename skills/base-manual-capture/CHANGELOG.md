# 变更记录

## 0.1.5 - 2026-08-25

- Public OSS metadata uses the `public` namespace and `seedforge` owner, and source resolution now uses public-registry instead of the retired private registry label.

## 0.1.4 - 2026-08-14

- frontmatter 规范化：SKILL.md 统一 LF / 无 BOM / 单一 YAML frontmatter 块，修复 AI IDE 加载告警（missing YAML frontmatter delimited by ---）。
## 0.1.3 - 2026-08-06

- 治理清欠：结构合规修复后版本抬升（ref_link、refs）。

## 0.1.2 - 2026-07-27

- 新增 SOP-B0“采集范围确认”人工确认点：开采前功能盘点 → 用户勾选覆盖范围 → 落为 flow 清单；防止漏采（如仅采 3 页而漏掉 20+ 子表单）。
- SOP-B5 退出门禁收紧：flow 清单全部处理完毕才算采集完成，交写作层前向用户报覆盖对账。

## 0.1.1 - 2026-07-27

- 新增 REFERENCE-CAPTURE-PITFALLS.md（P1~P5 坑库：SPA polling timeout, headless layout collapse, SPA route guard, Windows GBK crash, toast timing）；post_install_hints 增加提示。

## 0.1.0 - 2026-07-27

- 新建 `base-manual-capture`：域中立、工具中立的操作手册截图采集基座。
- 定义 B 阶段主流程（SOP-B1~B5）：环境确认 → 逐步采集+用户确认 → 异常分支 → 产物落盘 → 退出门禁。
- 定义采集产物契约（capture-ledger + capture-trace）、截图命名规范、脱敏规则三份 references。
- 预留 C 化章节（回放脚本规则与 diff 刷新）与 Client 采集通道扩展位（本版仅 web）。
- 与 `pg-manual-builder` 通过 capture-ledger 交接：采集与写作解耦。
