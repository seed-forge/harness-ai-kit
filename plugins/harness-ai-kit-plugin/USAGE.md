# harness-ai-kit-plugin 使用说明

## 安装

```bash
harness-ai-kit install plugin harness-ai-kit-plugin --profile web
# 或本地联调：
dsh plugin --profile scratch add ./plugins/harness-ai-kit-plugin
dsh --profile scratch --dump-config   # 应包含 harness-ai-kit-plugin 层
```

## 可直接复制的中文 Prompt

```text
用 harness-ai-kit 工具查一下团队发布过哪些 CLI，然后看 harness-ai-kit 的详情。
```

```text
帮我把 harness-ai-kit-ops 技能装到当前项目（runtime dsh，project 作用域）。
```

```text
检查一下 dsh 环境（版本基线与 profile 状态）。
```

```text
在团队资产里搜一下 kafka 相关的技能。
```

## 卸载

```bash
harness-ai-kit uninstall plugin harness-ai-kit-plugin --profile web
# 或：dsh plugin --profile web remove harness-ai-kit-plugin
```

## 说明

- 本插件只注册一个工具入口 + 随包注册 `harness-ai-kit-ops`（精简版）技能；
  其余技能不注入，技能正文按需加载（Token 治理 D11/D12）。
- 安装类动作会落入 dsh 权限审批流。
