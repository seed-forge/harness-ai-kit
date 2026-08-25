# dsh 集成示例

- `hello-plugin/`：最小 dsh 插件（工具注册）。
- 团队技能 demo：`harness-ai-kit install skill harness-ai-kit-ops --runtime dsh --scope project`
  后，dsh 会话 `<available_skills>` 可见（rank 200 原生扫描）。
- 完整插件：`plugins/harness-ai-kit-plugin/`（publish/install 全链见 docs/dsh-integration.md）。
