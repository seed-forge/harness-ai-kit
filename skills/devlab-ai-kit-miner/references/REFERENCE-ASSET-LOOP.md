# Loop 资产创建规范

## 何时选择 Loop

- 需要周期性闭环检查或循环排障
- "诊断→验证→修复→验收"迭代模式
- 触发-执行-验证的稳定闭环

## Loop 子类型

Loop 不是单一模式。根据问题类型，循环结构、退出条件、Maker/Checker 职责完全不同。

### 1. 排障型 Loop（Troubleshoot）

**信号**：症状已知但根因不明，需要"猜测→验证→修复→再验证"迭代。

**循环结构**：
```
输入：症状描述 + 上下文
→ 分类症状 → 定位根因 → 生成修复方案 → 执行修复
→ Checker 验证（测试通过/服务恢复）
→ 未通过 → 回到"定位根因"，带上一轮失败信息
→ 通过 → 输出修复报告
```

**收敛条件**：测试通过 / 服务恢复 / 最大迭代 N 次 / 连续失败 M 次放弃

**命名**：`*-troubleshoot-loop`

### 2. 质量门禁型 Loop（Quality Gate）

**信号**：已有实现代码，需要循环"测试→修复→重测"直到达标。

**循环结构**：
```
输入：实现代码 + 测试套件 + 质量阈值
→ 运行测试 → 分析失败 → 修复代码 → 重新运行
→ pass rate ≥ 阈值？ → 输出通过报告
→ 未达标 → 回到"分析失败"
```

**收敛条件**：pass rate ≥ 阈值 / 最大迭代 N 次 / 连续 2 轮无改善

**命名**：`*-quality-loop` 或 `*-test-fix-loop`

### 3. 巡检型 Loop（Monitor/Inspect）

**信号**：需要持续或周期性检查某项指标/状态。

**循环结构**：
```
输入：检查目标 + 间隔 + 告警条件
→ 等待间隔 → 执行检查 → 状态正常？ → 继续等待
→ 状态异常 → 告警/自愈 → 重新检查
```

**收敛条件**：持续运行（无自然终止）/ 外部停止信号

**命名**：`*-monitor-loop` 或 `*-inspect-loop`

### 子类型速查表

| 维度 | 排障型 | 质量门禁型 | 巡检型 |
|------|--------|-----------|--------|
| **目标** | 找到并修复根因 | 达到质量阈值 | 持续保障状态正常 |
| **循环单元** | 诊断→修复→验证 | 测试→修复→重测 | 等待→检查→告警/自愈 |
| **Maker** | 诊断 + 修复 | 分析 + 修复 | 检查 + 自愈 |
| **Checker** | 独立验证修复效果 | 运行测试 + 统计达标 | 判断状态 + 升级判断 |
| **命名** | `*-troubleshoot-loop` | `*-quality-loop` | `*-monitor-loop` |

## Loop 目录结构

```
loops/{id}/
├── loop.json     # 元数据 + loop_specific 配置
├── LOOP.md       # Maker 入口文件
├── CHECK.md      # Checker 入口 + rubric
├── USAGE.md      # 使用说明
└── CHANGELOG.md  # 版本历史
```

## loop.json 必填字段

| 字段 | 说明 |
|------|------|
| `schema_version` | 固定 `"1"` |
| `namespace` | 资产命名空间 |
| `id` | Loop 唯一标识 |
| `version` | 语义化版本 |
| `package_type` | 固定 `"loop"` |
| `loop_specific.maker` | Maker 入口文件和描述 |
| `loop_specific.checker` | Checker 入口、rubric 定义 |
| `loop_specific.stop_conditions` | success / failure / budget 条件 |
| `loop_specific.convergence_metric` | 收敛指标和方向 |

## LOOP.md 标准结构

```markdown
# {Loop 名称} - Maker Entry
## Role
## Pipeline / 工作流步骤
## Known Pitfalls
## Output Format
```

## CHECK.md 标准结构

```markdown
# {Loop 名称} - Checker Entry
## Role
## Anti-Injection Notice
## Rubric（Dimension / Weight / Severity / Verification）
## Evaluation Steps
## Verdict（PASS / RETRY / FAIL / ESCALATE）
```

## Skill + Loop 联动模式

当复盘发现的经验同时满足以下两个条件时，应同时产出 Skill 和 Loop：

1. **Skill**：提供知识参考（库文档、踩坑经验、API 模式）
2. **Loop**：提供循环流程（Maker 执行 → Checker 验证 → 迭代）

**为什么需要 Loop 而不只是 Skill**：
- 排障类经验不可能穷举所有踩坑以 Skill 记录
- Loop 把 HUMAN-IN-THE-LOOP 编程为 HUMAN-ON-THE-LOOP
- Loop 有收敛条件，避免无限循环
