# Dify 模型命名与配置规范

将 NewAPI 等聚合网关的模型接入 Dify 时的命名约定与最佳实践。

## 模型命名约定

### LLM 模型

```
{系列}-{规格}-{变体}
```

| 组件 | 规范 | 示例 |
|------|------|------|
| 系列 | 使用上游官方名称，小写 | `gpt`, `claude`, `deepseek`, `qwen`, `glm` |
| 规格 | 版本号 + 能力级别 | `5.4`, `sonnet-4.5`, `v4-pro` |
| 变体 | 可选，标注特殊能力 | `thinking`, `flash`, `max` |

**推荐格式**：
```
gpt-5.4                          # 标准模型，直接用上游名
claude-sonnet-4.5                # Anthropic 模型
deepseek-v4-pro                  # DeepSeek 旗舰
qwen3.5-plus                     # Qwen 增强版
grok-4-thinking                  # 带思考模式
```

**避免的格式**：
```
❌ NewAPI-GPT5.4                 # 不要前缀供应商名
❌ gpt-5.4 (NewAPI)              # 不要在模型名中加注释
❌ GPT_5_4                       # 统一用连字符
```

### Embedding 模型

```
{系列}-{规模}-{版本}
```

示例：`bge-m3`, `text-embedding-v1`

### Rerank 模型

使用上游名称，不添加额外前缀。

示例：`bge-reranker-v2-m3`

### Speech/TTS 模型

使用上游名称。

示例：`SenseVoiceSmall`, `ChatTTS`

## Credential 命名约定

在 Dify 中，所有通过同一网关（如 NewAPI）接入的模型应共享同一个 credential name：

```
newapi-{环境}
```

| 环境 | Credential Name |
|------|----------------|
| 组织内部集群 生产 | `newapi-组织内部集群` |
| 组织内部集群 测试 | `newapi-组织内部集群` |

**规则**：
- 同一网关的所有模型使用同一个 credential name
- 不同 consumer key 可以使用不同的 credential name
- 每次添加模型时，如果 credential name 已存在，Dify 会复用已有凭据

## Provider YAML 规范

```yaml
# newapi-组织内部集群.yaml — 将 NewAPI 组织内部集群 接入 Dify
provider:
  type: openai-api-compatible   # NewAPI 统一走 OpenAI 兼容格式
  name: "NewAPI 组织内部集群"         # credential name，所有模型共享
  credentials:
    api_base: "http://<service-url>:13033/v1"
    api_key: "${NEWAPI_CONSUMER_KEY}"  # 环境变量引用，勿硬编码

  models:
    # GPT 系列
    - model: "gpt-5.4"
      max_tokens: 128000
    - model: "gpt-5.5"
      max_tokens: 128000

    # Claude 系列
    - model: "claude-sonnet-4.5"
      max_tokens: 200000
    - model: "claude-haiku-4.5"
      max_tokens: 200000

    # DeepSeek 系列
    - model: "deepseek-v4-pro"
      max_tokens: 128000
    - model: "deepseek-v4-flash"
      max_tokens: 128000

    # Embedding
    - model: "bge-m3"
      model_type: "text-embedding"
    - model: "bge-reranker-v2-m3"
      model_type: "rerank"
```

## 模型类型映射

| Dify model_type | 适用场景 | 新增命令示例 |
|-----------------|---------|-------------|
| `llm` | 对话/补全/推理 | `difyctl provider add --from provider.yaml` |
| `text-embedding` | 向量化 | `--model-type text-embedding` |
| `rerank` | 重排序 | `--model-type rerank` |
| `speech2text` | 语音识别 | `--model-type speech2text` |
| `tts` | 语音合成 | `--model-type tts` |

## 模型可用性检查

添加前先确认模型在 NewAPI 中实际可用：

```bash
# 检查 consumer key 能访问的所有模型
curl -sS -H "Authorization: Bearer $NEWAPI_CONSUMER_KEY" \
  http://<service-url>:13033/v1/models | jq '.data[].id'
```

只有 `/v1/models` 返回的模型才能成功添加到 Dify。如果模型返回 401，说明该 consumer key 未关联对应渠道，需要在 NewAPI 管理端关联。

## 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| 401 Invalid API key | consumer key 未关联该渠道 | NewAPI 管理端 → 用户 → 关联渠道 |
| 500 upstream error | 上游模型不可用 | `newapictl probe run --channel-id N` |
| 404 model | 模型名拼写错误或未开通 | 检查 `/v1/models` 返回的精确名称 |
| 模型列表已存在 | credential name + model 组合重复 | 使用相同 credential name 或先 remove |
