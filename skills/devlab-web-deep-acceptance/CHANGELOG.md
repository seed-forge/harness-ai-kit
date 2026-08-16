# 变更记录

## 0.1.2 - 2026-08-14

- frontmatter 规范化：SKILL.md 统一 LF / 无 BOM / 单一 YAML frontmatter 块，修复 AI IDE 加载告警（missing YAML frontmatter delimited by ---）。
## 0.1.1 - 2026-08-07

- 修复 skill.json `relates_to` 条目 `target` 字段后缺失逗号的 JSON 语法问题。

## 0.1.0 - 2026-08-03

- 初始化 devlab-web-deep-acceptance：从大型存量 Web 系统深度验收实战（72 条陷阱实证）通用化提取。
- 七阶段方法论：系统画像 → registry 建模 → 预检四段 → 分级执行 → 假成功甄别 → 三对齐审计 → 报告回写。
- 执行器通用化：run.js 唯一入口七模式 + lib 六件套，环境差异全部收敛 e2e.config.js。
- references 五份：GRADING / FALSE-SUCCESS / REGISTRY-SCHEMA / BLOCKED-TAXONOMY / PITFALLS（72 条五段式）。
- templates 六件套 + decisions.yaml（HD-1 高危写操作 / HD-2 环境故障处置）。
