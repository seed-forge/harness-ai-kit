# infra-ragflow-ops Usage

Use this skill for RAGFlow platform operations.

## 常用命令

```powershell
ragflowctl doctor --profile 组织内部集群 --json
ragflowctl dataset list --json
ragflowctl probe --json
```

## 可直接复制的中文 Prompt

```text
请使用 infra-ragflow-ops 检查 <host> 的 RAGFlow：先运行 ragflowctl doctor，再检查模型、向量库、对象存储和数据库依赖。需要消费模型或数据源时，分别联动 infra-aimodel-ops 和 infra-datasource-ops。
```
