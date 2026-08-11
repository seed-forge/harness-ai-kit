# MCP / Subagent 资产创建规范

## MCP（Model Context Protocol Server）

### 何时选择 MCP

- 需要连接外部 API/服务
- 为 AI agent 提供新的工具能力
- 封装第三方系统的交互协议

### MCP 目录结构

```
mcps/{id}/
├── SERVER_METADATA.json  # 元数据
└── tools/
    └── {tool-name}.json  # 工具定义（JSON Schema）
```

### MCP 命名规范

- ID：按功能命名，如 `gitea-api`、`nexus-api`
- 工具名：动词 + 名词，如 `create_repository`、`list_issues`

### MCP 部署方式

| 类型 | 说明 | 场景 |
|------|------|------|
| STDIO | MCP Hub 托管的本地进程 | 内部工具、CLI 封装 |
| SSE/HTTP | 远程服务 | 外部 API 代理 |

### MCP 与 HiMarket 的分工

- **MCP Hub**：托管 STDIO 类型 MCP Server，提供统一入口
- **HiMarket**：Skill 市场，管理 Skill 的分发和安装
- MCP 提供工具能力，Skill 提供使用时机判断

---

## Subagent

### 何时选择 Subagent

- 需要独立的 Agent 角色（有自己的 system prompt）
- 任务需要专门的推理风格或领域知识
- 作为多 agent 协作中的一个节点

### Subagent 目录结构

```
.agents/
└── {id}/
    └── AGENT.md  # Agent 定义：角色、能力、约束
```

### Subagent 命名规范

- 按角色命名：`code-reviewer`、`security-auditor`
- 按领域命名：`frontend-expert`、`database-architect`

### Subagent vs Skill

| 维度 | Subagent | Skill |
|------|---------|-------|
| 执行方式 | 独立 Agent 实例 | 当前 Agent 的指令集 |
| 上下文 | 独立上下文 | 共享上下文 |
| 适用场景 | 需要专门推理风格 | 提供 SOP/知识参考 |
| 并发能力 | 可并行执行 | 串行执行 |
