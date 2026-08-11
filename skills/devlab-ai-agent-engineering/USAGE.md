# devlab-ai-agent-engineering — Usage

## Overview
AI Agent / LLM 应用工程化方法论技能：帮你把一个 AI 智能体应用拆分为可测试的分层管道，做规则/LLM 分工、多模型触点路由、Prompt 治理、韧性(超时/缓存/降级)与多厂商适配，并对照各域已知坑做结构性风险自查。

## When to use
- 新建任意 LLM 驱动应用前的架构设计。
- 现有 Agent 应用规则/LLM 边界混乱、Prompt 散落、成本失控时的重构梳理。
- 评审 AI 应用设计是否踩结构性坑。

## References
- `references/REFERENCE-NL2SQL.md` — NL2SQL/Text2SQL 落地范例与坑
- `references/REFERENCE-RPA.md` — 桌面 RPA/GUI 自动化落地范例与坑
- `references/REFERENCE-DIGITALHUMAN.md` — 语音数字人前端落地范例与坑

## 可直接复制的中文 Prompt

```text
用 devlab-ai-agent-engineering 帮我设计这个 AI 应用的分层架构：
- 业务目标：<一句话>
- 输入/输出形态：<自然语言查询 / 桌面操作 / 语音对话 / ...>
- 约束：延迟 <?>、成本 <?>、可解释性 <?>、私有化 <?>
请输出：分层管道 + 各层职责边界、规则/LLM 分工与兜底/超时/缓存策略、
多模型触点路由表、Prompt 治理方案，并对照同域已知坑做结构性风险自查。
```
