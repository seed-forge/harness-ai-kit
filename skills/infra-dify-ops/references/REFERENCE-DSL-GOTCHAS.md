# REFERENCE: Dify DSL 踩坑与校验维度

> 踩坑清单改编自 yoloyolo8/dify-workflow-writer（MIT）；校验维度参考
> yzmw123/dify-workflow-dsl-skill 的公开检查清单（实现由 `difyctl/dsl_validate.py` 自研）。

## Top Gotchas

1. **变量语法必须双 `#`**
   - ❌ `{{1718352852007.text}}`、`{{#1718352852007.text}}`、`{{{#...#}}}`
   - ✅ `{{#1718352852007.text#}}`
2. **Code 节点每个返回字段必须在 `outputs` 声明**，否则运行时报错。
3. **禁用 `error` 作为输出变量名**（与系统错误处理冲突，导致 JS 执行错误）；用 `error_message`。
4. **边连接不完整 = 工作流断裂**：每个可执行节点都要有入边/出边，非触发型 workflow 必须能到达 `end`。
5. **节点 ID 用 13 位毫秒时间戳字符串**，加引号、全图唯一。
6. **LLM 节点缺 `context` 对象**：即使 disabled 也要 `context: {enabled: false, variable_selector: []}`。
7. **`version` 未加引号**：Dify 导入要求 `version` 是字符串。
8. **凭据硬编码**：禁止把 API key / 数据库密码 / webhook secret 写进 DSL；用 `{{#env.API_KEY#}}` 或占位符。
9. **LLM 节点缺 `retry_config`**：模型返回 429/5xx/超时时整个 workflow 直接崩溃；`difyctl` scaffold 默认注入 3 次重试，手写或导出的 DSL 应检查是否缺失。
10. **LLM 节点缺 `error_strategy`**：重试耗尽后无 fallback，下游节点因拿不到输出而报错；建议配 `default_value` 让 workflow 降级继续。

## `difyctl dsl validate` 校验维度

| 维度 | 说明 | 级别 |
|------|------|------|
| version 类型与取值 | 必须是 `"0.6.0"`/`"0.7.0"` 字符串 | error |
| kind | 必须 `app` | error |
| mode | 必须是合法 mode；`agent` 需 0.7.0 | error |
| target-version 匹配 | `--target-version` 指定时须一致 | error |
| 节点 id 唯一 | 重复 id 报错 | error |
| 图端点 | 至少一个 `start`；advanced-chat 恰好一个 start | error |
| 可达性 | 所有可执行节点从 start 可达 | error |
| 终端节点 | workflow 可达 `end` / advanced-chat 可达 `answer` | warning |
| 环检测 | 图中不得有环 | error |
| edge 引用 | source/target 必须存在 | error |
| if-else handle | 出边 handle 是 case id 或 `false` | error |
| LLM 必填 | `model`/`prompt_template`/`context` | error |
| LLM 缺 retry_config | 未配 `retry_config` 或 `retry_enabled=false` | warning |
| LLM 缺 error_strategy | 未配 `error_strategy` | warning |
| Code outputs | 非空且不含 `error` 保留名 | error |
| 变量引用 | node-id 部分 1–50 word chars 且指向已知节点 | error |
| 单 `#` 引用 | `{{...}}` 缺 `#` 标记 | warning |

## 生产可用判定

- `published workflow` 存在且 `apps.workflow_id` 指向它（非 draft）。
- app API 黑盒调用不再停在 schema 校验/参数缺失。
- 健康样例 + 异常样例双验证通过；`workflow_runs` 收敛到 `succeeded`。

## 双轨导入排障

- API 轨返回 4xx：多为 cookie 缺 `csrf_token`（纯 session_cookie 会 401）或 DSL 版本不被目标 Dify 接受 → 修凭据/降版本，不要盲目降级浏览器。
- API 轨返回 5xx / 网络错误：`--via auto` 自动降级 Playwright。
- `status=pending`：版本不匹配需确认，`difyctl` 自动调 confirm 接口。
- 浏览器轨依赖 Studio 中文登录页与 `/apps` 流程；选择器可能随 Dify 版本漂移。
