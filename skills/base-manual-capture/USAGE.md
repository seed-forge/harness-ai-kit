# base-manual-capture Usage

## When To Use
- 需要 AI 自主操作一个可访问系统（有地址+测试账号）并逐步截图、生成操作手册配图时。
- 需要逐步走查系统流程并与用户交互确认业务概念/流程是否符合预期（B 阶段）时。
- 需要刷新旧手册截图，或把已确认路径固化为回放脚本（C 化）时。

## Inputs
- 系统地址、测试账号（口令仅登录用，不落产物）、功能流程描述、手册目标读者、输出目录（project_root / manual_root）。

## Output
- 截图文件（captures/<flow>/）、截图台账 capture-ledger.md、操作路径记录 capture-trace.yaml，可选草稿手册骨架。

## 可直接复制的中文 Prompt
### 场景 1：采集一条流程
```text
请使用 `base-manual-capture` 技能为我采集操作手册截图。
系统地址：<地址>；测试账号：<账号>（口令我单独给，勿写入任何产物）。
要采的流程：<一句话描述，如"登录后创建工单并提交审核">。
要求：按 SOP-B1~B5 执行，每步先截图再向我复述你的理解并等我确认/纠偏；
产出 capture-ledger.md、capture-trace.yaml 和截图，遵循脱敏规则。
```

### 场景 2：交给写作层成稿
```text
采集完成后，请调用 `pg-manual-builder`，以 capture-ledger.md 作为截图清单，
按其章节结构和图文绑定规则生成手册草稿，并跑 SOP 5.5 质检门禁。
```

## Fast Path
- 先读 `SKILL.md`。
- 采集前确认浏览器工具（Playwright MCP / browser-use MCP / 本地 playwright）任一可用。
- 契约字段见 `references/REFERENCE-CAPTURE-CONTRACT.md`。
