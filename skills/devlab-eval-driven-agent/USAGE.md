# devlab-eval-driven-agent — Usage

## Overview
eval 自评测体系驱动的 AI Agent 生产体系：评测集组织 + Mock 隔离 + 标准化比对 + 自动评测脚本 + 回归门禁；
L0-L4 分层评测（确定性单测 / 轨迹评测 / 输出评测 / 生产回归 / 安全成本护栏），L1 golden session 轨迹断言，
L2/L3 数据后端接 Langfuse（dataset/scores/LLM-as-judge），配套 `evalctl` CLI 承接 run/diff/ingest/feedback/report。

## When to use
- 输出可判定正确性的 AI 应用（NL2SQL/RAG/分类）。
- 多步工具调用 Agent（需要验证工具选择/顺序/恢复/停止等轨迹行为）。
- 频繁改 prompt/规则/模型需快速判断有无回归。
- 需要可量化质量指标。

## 可直接复制的中文 Prompt

```text
用 devlab-eval-driven-agent 给这个应用搭评测体系：
1) 定义"什么算对"与比对方式（如 SQL 标准化后比对）；
2) 按业务模块组织评测集，每条含输入+期望输出；
3) 搭自动评测脚本（可单用例/单模块跑、Mock 下游、免真实环境）；
4) 接入回归门禁（改动合入前跑，守正确率基线）。
后续请评估是否值得下沉一个 evalctl CLI 做真实数据采集与反馈回流。
```

```text
用 devlab-eval-driven-agent 给这个多步 Agent 搭 L1 轨迹评测：
1) 为每个核心场景建 golden-sessions/<scenario>/session.yaml（输入 + expected_trace + recovery + stop_conditions + expected_terminal）；
2) 用 ToolSimulator mock 全部工具（含可注入故障的 tool_error），replay 后逐 step 比对轨迹；
3) 接入 CI 作为回归门禁（工具调用次数/终态/恢复路径不达标即 FAIL）；
4) 线上 Langfuse session 确认正确的轨迹 → 沉淀为新的 golden session。
```

## 备注
- 每修一个线上 badcase → 补一条回归用例。
- 每修一个"轨迹类" badcase → 补一条 golden session（工具选错/顺序错/不恢复）。
- 真实数据回流须脱敏合规；评测集不得含真实凭据/隐私。
