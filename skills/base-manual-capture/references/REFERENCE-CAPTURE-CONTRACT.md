# REFERENCE: 采集产物契约（capture-ledger + capture-trace）

采集层与写作层通过以下两个文件对接。字段是稳定契约，写作层（pg-manual-builder）与后续 C 化都依赖它。

## 1. 截图台账 capture-ledger.md

每条流程一份（或多流程合并，用 `flow` 区分）。Markdown 表格，供人审阅 + 写作层回填。

| 列 | 含义 | 必填 |
|---|---|---|
| step_id | 步骤编号，形如 `01`、`02`、`03a`（分支步加后缀字母） | 是 |
| flow | 所属流程名（英文短标识，如 `create-order`） | 是 |
| page | 页面/模块名（与系统界面一致） | 是 |
| screenshot | 截图相对路径 `captures/<flow>/<step_id>-<page>.png` | 是 |
| entry | 操作入口：菜单路径/按钮位置/页面名 | 是 |
| action | 具体动作：点击/输入/选择/提交/确认 | 是 |
| result | 预期结果：页面变化/状态变化/数据变化 | 是 |
| notes | 注意事项：权限限制/字段约束/常见误操作 | 否 |
| branch | 所属分支：`main` 或异常分支名（如 `no-permission`） | 是 |
| confirm | 用户确认状态：`confirmed` / `corrected` / `pending` | 是 |
| redacted | 脱敏标记：是否含打码，`yes`/`no` | 是 |

### 示例

```markdown
| step_id | flow | page | screenshot | entry | action | result | notes | branch | confirm | redacted |
|---|---|---|---|---|---|---|---|---|---|---|
| 01 | login | 登录页 | captures/login/01-登录页.png | 浏览器打开系统地址 | 输入账号密码点击登录 | 进入系统首页 | 密码错误会提示锁定 | main | confirmed | yes |
| 02 | create-order | 工单列表 | captures/create-order/02-工单列表.png | 左侧菜单「工单管理」 | 点击「新建工单」 | 打开新建工单表单 | 需「工单员」角色 | main | confirmed | no |
```

## 2. 操作路径记录 capture-trace.yaml

供 C 化（回放脚本生成）使用，手册正文不引用。凭据一律占位符。

```yaml
flow: create-order
channel: web
status: in-progress   # in-progress | C-ready
viewport: { width: 1920, height: 1080 }
base_url: "<系统地址>"
steps:
  - step_id: "02"
    url: "/order/list"
    selector: "button:has-text('新建工单')"   # 或稳定的元素描述
    action: click                              # click | fill | select | press | goto | wait
    value: null                                # fill/select 时的值；凭据用 ${VAR} 占位
    wait_condition: "form.order-create visible"
    screenshot: "captures/create-order/02-工单列表.png"
  - step_id: "03"
    url: "/order/create"
    selector: "input[name='title']"
    action: fill
    value: "示例工单标题"
    wait_condition: null
    screenshot: "captures/create-order/03-新建工单表单.png"
```

## 契约稳定性说明

- 0.1.x（trial）期间允许对字段做破坏性调整，稳定后锁定
- 写作层只读 `capture-ledger`；`capture-trace` 仅采集层与 C 化工具读写
- `step_id` 在 ledger 与 trace 中必须一致，是两文件的关联键
