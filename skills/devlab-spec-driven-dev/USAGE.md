# devlab-spec-driven-dev — Usage

## Overview
通用 spec 驱动的 AI 协作开发方法论：需求 → requirements/design/tasks 三件套提案（事实源）→ 人类审查门禁 → Run all tasks 分任务执行 → 回归。工具无关，Kiro spec 为一个 example。

## When to use
- 中大型功能/重构、需要拆解与阶段验收。
- 跨会话续跑、需要稳定事实源承接进度。
- 关键决策需人类把关的 AI 协作开发。

## References
- `references/REFERENCE-KIRO-SPEC-EXAMPLE.md` — Kiro `.kiro/specs/` 具体落地范例。

## 可直接复制的中文 Prompt

```text
用 devlab-spec-driven-dev 推进这个需求：
1) 先产出 specs/<name>/ 的 requirements.md（逐条可验证），我确认；
2) 再出 design.md（含破坏性变更影响面、可复用库调研），我确认；
3) 拆 tasks.md（可勾选、含顺序），我确认；
4) 我说 Run all tasks 后再逐任务执行并同步状态。
约束：提案与注释中文、允许破坏性变更但同步调用侧、工程化思维、减少不必要测试。
关键决策请给我"方向1(推荐)/方向2"选项。
```
