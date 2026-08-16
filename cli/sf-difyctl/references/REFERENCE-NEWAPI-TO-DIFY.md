# NewAPI → Dify 端到端配置流程

将 NewAPI 渠道接入 Dify 作为模型供应商的完整操作手册。

## 前提

- NewAPI 已部署运行（由 `infra-newapi-ops` 技能管理）
- Dify 已部署运行
- 已安装 `newapictl` 和 `difyctl`（v0.3.0+）
- 已配置 difyctl profile（含 console_key）

## 流程概览

```
NewAPI                            Dify
  │                                │
  ├─ channel add (newapictl) ──┐   │
  │                            │   │
  │  获取 API endpoint + key   │   │
  │                            │   │
  │                            ▼   │
  │                    provider YAML│
  │                            │   │
  │                            ▼   │
  │                  provider add ──┤
  │                  (difyctl)   │
  │                                 │
  │                  provider test ─┤
  │                                 │
  ▼                                 ▼
```

## Step 1: 在 NewAPI 创建渠道

```bash
# 准备渠道 YAML（参考 infra-newapi-ops 的 REFERENCE-CHANNEL-YAML）
newapictl --profile 组织内部集群 channel add --from ./openai-channel.yaml
```

## Step 2: 准备 Dify Provider YAML

基于渠道信息创建 `newapi-provider.yaml`：

```yaml
provider:
  type: openai-api-compatible
  name: "NewAPI 组织内部集群"
  credentials:
    api_base: "http://<service-url>:13033/v1"
    api_key: "${NEWAPI_API_KEY}"
  models:
    - model: "gpt-4o"
      max_tokens: 128000
    - model: "gpt-4o-mini"
      max_tokens: 128000
    - model: "claude-opus-4-8"
      max_tokens: 200000
  options:
    load_balancing: true
```

## Step 3: 在 Dify 配置模型供应商

```bash
# 预览（不实际创建）
difyctl --profile 组织内部集群 provider add --from newapi-provider.yaml --dry-run

# 确认后创建
difyctl --profile 组织内部集群 provider add --from newapi-provider.yaml
```

## Step 4: 验证连通性

```bash
difyctl --profile 组织内部集群 provider test --provider "NewAPI 组织内部集群" --model gpt-4o-mini
```

## Step 5: 查看已配置的供应商

```bash
difyctl --profile 组织内部集群 provider list --json
```

## 批量导入多供应商

```yaml
# providers-manifest.yaml
providers:
  - type: openai-api-compatible
    name: "NewAPI OpenAI"
    credentials:
      api_base: "http://<service-url>:13033/v1"
      api_key: "${NEWAPI_OPENAI_KEY}"
    models:
      - model: "gpt-4o"
      - model: "gpt-4o-mini"

  - type: openai-api-compatible
    name: "NewAPI Claude"
    credentials:
      api_base: "http://<service-url>:13033/v1"
      api_key: "${NEWAPI_CLAUDE_KEY}"
    models:
      - model: "claude-opus-4-8"
      - model: "claude-sonnet-4-6"
```

```bash
# 预览
difyctl --profile 组织内部集群 provider batch --manifest providers-manifest.yaml --dry-run

# 执行
difyctl --profile 组织内部集群 provider batch --manifest providers-manifest.yaml --apply
```

## 环境变量

| 变量 | 说明 |
|------|------|
| `DIFY_CONSOLE_KEY` | Dify Console 认证凭据（Admin API Key 或 session cookie） |
| `NEWAPI_API_KEY` | NewAPI 渠道的 API Key |

## Profile 配置示例

`~/.difyctl/config.json`:
```json
{
  "profiles": {
    "组织内部集群": {
      "base_url": "http://<service-url>",
      "console_key": "${DIFY_组织内部集群_CONSOLE_KEY}",
      "auth_type": "bearer",
      "providers_dir": "~/.difyctl/providers/组织内部集群"
    }
  },
  "active_profile": "组织内部集群"
}
```

## 故障恢复

- **Console API 不可用**: `provider add` 会自动回退到 Playwright browser 模式（需配置 `DIFY_STUDIO_USERNAME`/`DIFY_STUDIO_PASSWORD`）
- **禁用 browser 回退**: `difyctl --no-browser-fallback provider add --from x.yaml`
- **认证失败 (401)**: 检查 console_key 是否正确，重新获取
