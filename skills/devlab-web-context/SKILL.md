---
name: devlab-web-context
description: 前端项目上下文理解规则资产（<domain>-context 家族首个成员）：双模式（模式 A 规则包被 devlab-context-bootstrap 文件契约委托 / 模式 B 独立四步渐进式理解），产出前端 context 画像（7 固定键 + 置信度标注），供 bootstrap 消费填五件套台账。
---

# devlab-web-context — 前端项目上下文理解规则资产

> `<domain>-context` 家族（web/srv/infra/tool）首个成员。只提供 **Understand Capability**：
> 规定"什么时候理解、理解什么、理解到什么程度"，产出前端 context 画像，不生产五件套台账。

## 定位与边界

- **本技能是什么**：web 域前端项目上下文理解规则（信号表 + 特有条目 + 渐进式理解工作流）。
- **本技能不是什么**：不生产 `.harness/devlab/` 五件套台账（那是 `devlab-context-bootstrap` 的职责）；不是工程化能力层（那是 `devlab-web-engineering`）；不自建 CLI（社区 CLI/MCP/Skill 引用策略见 bootstrap 通用层）。
- **家族化**：与未来的 `devlab-srv-context` / `devlab-infra-context` / `devlab-tool-context` 同构——共享 bootstrap 通用层（四原则全文 + 社区引用 + 五件套骨架），本技能只承载 web 领域规则。

## 四原则（一句话摘要）

> 完整原则全文在 `devlab-context-bootstrap`（缺失时本摘要可独立指导行为）。

1. **context-before-change**：改动任何代码前先建立最小上下文，禁止在未知项目状态下动手。
2. **evidence-before-assumption**：画像条目只写实证（读到的配置/跑通的命令）；推断必须标注依据；未验证标 `todo`。
3. **progressive-understanding**：按需加深，最小上下文起步，置信度不达标才 Deepen，不做一次性全量理解。
4. **re-understand**：执行中发现认知偏差（命令跑不通/现象与画像不符）立即回退重理解，不将错就错。

## 双模式入口

### 模式 A：规则包模式（被 bootstrap 委托）

**触发方**：`devlab-context-bootstrap` Phase 0 判定 frontend-web 后。

**执行**：
1. 判定前端子类型（信号文件）：有 `qiankun`/`micro-app`/自研 shell 注册配置 → `vue-microfrontend`；有 `react` + SPA 结构 → `react-spa`；默认 `vue-microfrontend`（当前实证最全）。
2. 读取 `profiles/<profile_type>.md`（子类型特有信号与条目）+ `references/REFERENCE-WEB-RULES.md`（跨子类型通用信号）。
3. 按信号表扫描项目，逐条产出画像维度（key/value/confidence/evidence/note）。
4. 画像写入 `.harness/devlab/context/<project>-web-context.yaml`（契约见下文）。
5. 返回给 bootstrap：画像路径 + 概要（profile_type / overall_confidence / 主要发现）。

### 模式 B：完整工作流模式（独立自编排）

**触发**：用户直接要求"理解这个前端项目 / 生成前端 context 画像"。

**工作流（四步循环）**：

```text
Task
 ↓
Identify Scope        # 项目根、子应用清单（monorepo 逐个）、理解目的（改代码/排障/验收）
 ↓
Build Minimal Context # 读 profiles/<type>.md + REFERENCE-WEB-RULES → 最小信号扫描
 ↓
Confidence Check      # 每条目标 confidence：confirmed 需 evidence；不足 → Deepen
 ↓
足够理解 → 产出画像并结束
不足 → Deepen Context  # 读更多配置/跑命令/查注册配置
认知偏差 → Re-understand  # 回退重扫，更新画像
```

**结束条件**：所有关键键达到 `confirmed` 或 `inferred`（无未解释的 `todo` 阻塞），或资源上限（扫描轮次/时间）。

**产出**：前端 context 画像（契约见下）。需落台账时 → 委托 `devlab-context-bootstrap`（镜像衔接：bootstrap 消费画像填五件套）。

## 画像契约

落点：`.harness/devlab/context/<project>-web-context.yaml`

```yaml
profile:
  project_name: <package.json name>
  profile_type: <vue-microfrontend | react-spa | ...>
  generated_by: devlab-web-context
  generated_at: <ISO 时间戳>
  overall_confidence: <high | medium | low>
items:
  - key: <tech_stack | dev_server | module_registry | dev_proxy | routing | build_deploy | component_library>
    value: <实证值或描述>
    confidence: <confirmed | inferred | todo>
    evidence: <文件:行 或 实际执行的命令>
    note: <备注，如 TODO 原因、处置规则>
```

**7 个固定键**：`tech_stack` / `dev_server` / `module_registry` / `dev_proxy` / `routing` / `build_deploy` / `component_library`。所有键必须出现在画像中（未识别的标 `todo` 保留骨架，不省略）。

**置信度规则**：
- `confirmed` 必须附 evidence（读到配置/跑通命令）；`inferred` 必须附推断依据；`todo` 保留骨架。
- 敏感信息（密码/令牌/私钥）永不写入 value，只写环境变量引用或"详见 <config_file>"。

## 依赖与降级

- `devlab-context-bootstrap`（optional）：完整四原则全文、社区引用、五件套骨架。缺失时本技能用内嵌摘要独立运行（模式 B 不受影响；模式 A 由 bootstrap 触发，天然在场）。
- `devlab-web-engineering`（optional）：其 Phase 1 扫描结果可作为信号输入源之一（如端口/包管理器），但非必需。

## Human Decisions

| ID | 决策点 | 触发条件 | 默认 |
|----|--------|----------|------|
| HD-W1 | 前端子类型判定 | 信号文件多命中或模糊 | 以用户确认的一句为准；默认 vue-microfrontend |
| HD-W2 | 敏感信息写入边界 | 画像涉及密码/令牌 | 必脱敏（环境变量引用或详见 <文件>），例外必问 |
| HD-W3 | 是否委托 bootstrap 落台账 | 模式 B 画像产出后 | 用户需要台账时委托；否则只留画像 |

## Integration Points

| 目标资产 | 类型 | 方向 | 契约（输入→输出） |
|---------|------|------|-----------------|
| devlab-context-bootstrap | skill | inbound/outbound | 模式 A：被委托按 profiles/ 规则扫描 → 画像；模式 B：画像 → bootstrap 消费填五件套 |
| devlab-web-engineering | skill | outbound | 可选：其 Phase 1 扫描结果（端口/包管理器/子应用）作为信号输入源 |
| devlab-srv-context | skill | sibling | 家族对称成员（同构契约，无直接调用；srv 域由 bootstrap 委托） |

## 约束

- 画像事实必须来自实证；推断必须标注，禁止编造连接串/版本号。
- 密码/令牌/私钥永不写入画像与输出。
- 文档用项目团队语言（中文项目用中文），命令用可复制形态。
- 模式 B 结束条件未达标时，输出"部分理解 + 阻塞点清单"，不假装完整。

## References

| 文件 | 内容 | 何时读 |
|------|------|--------|
| `references/REFERENCE-WEB-RULES.md` | 跨子类型通用 web 信号与扫描方法 | 模式 A/B 第一步必读 |
| `profiles/vue-microfrontend.md` | Vue2 微前端实证级信号与特有条目 | 判定命中时读 |
| `profiles/react-spa.md` | React SPA 骨架信号（模板级） | 判定命中时读 |
| `examples/vue-microfrontend-project.md` | 实证画像示例（契约格式样例） | 产出画像前参考 |
