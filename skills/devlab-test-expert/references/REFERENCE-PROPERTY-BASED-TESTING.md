# REFERENCE-PROPERTY-BASED-TESTING — 属性测试模式索引

## 定位

属性测试（Property-Based Testing, PBT）用生成器产生大量输入，验证"对所有输入都应成立"
的性质，替代只测少数例子的示例测试。本文件只浓缩关键模式并索引官方资料，不复制全文。

## 关键模式

| 模式 | 性质 | 典型场景 |
|------|------|---------|
| Roundtrip | `decode(encode(x)) == x` | 序列化 / 编解码 / 解析器 |
| Inverse | `f(g(x)) == x` | 加密解密 / 压缩解压 |
| Idempotence | `f(f(x)) == f(x)` | 排序 / 去重 / 幂等写 |
| Commutative / Associative | `f(a,b) == f(b,a)`、`f(f(a,b),c) == f(a,f(b,c))` | 数学运算 / 集合操作 |
| Invariant | 某种约束始终成立 | 数据校验 / 状态机不变量 |
| Stateful | 随机操作序列后不变量仍成立 | 购物车 / 队列 / 数据库事务 |
| Shrink | 失败时自动缩小到最小反例 | 所有 PBT 用例 |
| Precondition | 跳过不适用输入（非零除数等） | 过滤非法生成值 |

## 语言与工具映射

| 语言 | 工具 | 官方文档 |
|------|------|---------|
| TypeScript / JavaScript | fast-check | https://fast-check.dev/docs/ |
| Python | Hypothesis | https://hypothesis.readthedocs.io/ |
| Java | jqwik | https://jqwik.net/ |
| F# / .NET | FsCheck | https://fscheck.github.io/FsCheck/ |

## 使用要点

- 先找性质再写生成器：roundtrip / inverse / idempotence / invariant 是最高频起点。
- 生成贴近业务约束的输入，少用 `assume` 过滤；过滤太多会让测试变慢且覆盖面失真。
- 断言要具体，避免 `not null` 这类弱断言掩盖行为错误。
- 失败时先看 shrink 后的最小反例，再补示例测试固化回归。
- 与示例测试互补：关键业务路径保留示例用例，边界与组合场景交给 PBT。
- CI 中固定 seed / 支持复现，避免 flaky 时无法定位。

## 扩展阅读

- fast-check 官方教程：https://fast-check.dev/docs/tutorials/quick-start/
- Hypothesis 官方快速入门：https://hypothesis.readthedocs.io/en/latest/quickstart.html
- jqwik 用户指南：https://jqwik.net/docs/current/user-guide.html
- F# for fun and profit：https://fsharpforfunandprofit.com/posts/property-based-testing/
