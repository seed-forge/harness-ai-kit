# devlab-ai-kit-miner 用法

## 1. 安装

```bash
harness-ai-kit install skill devlab-ai-kit-miner
```

建议同时安装基础复盘能力：

```bash
harness-ai-kit install skill post-task-skill-miner
```

## 2. 研发会话后复盘

在一次较长的研发会话结束后触发：

```text
用 devlab-ai-kit-miner 复盘这次研发会话，判断有没有值得沉淀的内容。
```

## 3. 输出内容

- 是否建议沉淀
- 资产类型：Skill / CLI / MCP / Loop / Subagent / 知识卡片
- 沉淀位置：项目级 / 团队共享
- 候选资产最小规格草案
- 与现有 `devlab-*` 资产的关系（新增/补充/桥接/重复）
- Loop 候选的 6 信号评分结果（由 post-task-skill-miner 提供）

## 4. 衔接创建

复盘输出草案后，如需实际创建资产：

```text
用 ai-kit-forge 按上面的草案创建资产。
```

## 可直接复制的中文 Prompt

```text
请用 devlab-ai-kit-miner 复盘本次研发会话。
要求：
1. 识别本次涉及的技术领域和已联动的 devlab-* 资产
2. 判断哪些经验值得沉淀，沉淀为什么类型（Skill/CLI/MCP/Loop/Subagent/知识卡片）
3. 判断沉淀到项目级还是团队共享仓库
4. 给出候选资产的最小规格草案（名称、用途、输入、输出、工作流、约束）
5. 指出与现有 devlab-* 资产的关系（新增/补充/桥接/重复）
输出：复盘结论 + 沉淀建议 + 最小规格草案。
```
