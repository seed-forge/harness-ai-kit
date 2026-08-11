# Reference: 设计模式清单与示意性伪代码

> 本文是 `devlab-tech-debt-ops` 的 reference。目的是**给拆分方向的候选清单**，不是教程。
> 伪代码仅**示意**（点到即止）；具体是否用、怎么用、用哪个变体，由 AI Agent 结合项目现场给选项/建议。
> **反过度设计**：没有明确坏味道就不要引入模式。

## 何时考虑重构模式（坏味道 → 候选模式）

| 坏味道 | 候选方向 |
|--------|---------|
| god-class：一个类塞满职责 | 按职责抽取（Extract Class）+ 配置对象 + 策略 |
| 巨型 if/else / switch 按类型分支 | Strategy / 多态分发 / 表驱动 |
| 到处 new 具体类、难替换 | Factory / 依赖注入 |
| 多步骤流程硬编码在一处 | Pipeline / Chain of Responsibility / Template Method |
| 多厂商/多实现需可插拔 | Adapter / 接口 + 注册表 |
| 构造参数爆炸 | Builder / 配置对象 |
| 跨模块事件通知耦合 | Observer / 事件总线 |
| 重复的资源获取/清理 | RAII / 上下文管理器（with） |

## 典型模式（示意性伪代码）

### Strategy（按类型分策略，替代巨型分支）
```
interface Strategy: def handle(ctx) -> Result
registry = { "metric": MetricStrategy(), "ranking": RankingStrategy(), ... }
def dispatch(ctx):
    return registry[classify(ctx)].handle(ctx)   # 分类 → 选策略
# 用于：查询类型分派、消息类型处理。避免 if type==... 的长链。
```

### 配置对象（god-class 提取的第一刀）
```
@dataclass
class LayoutConfig:      # 把散落的布局/阈值参数聚成一处
    nav_ratio: float; chat_ratio: float; poll_interval: int
class Handler:
    def __init__(self, cfg: LayoutConfig): self.cfg = cfg
# 用于：把巨类里的"参数团"先抽走，立刻降复杂度。
```

### Adapter（隔离多厂商 SDK）
```
interface ASR: def start(); def on_text(cb)
class VendorAAdapter(ASR): ...   # 包装厂商 A SDK
class VendorBAdapter(ASR): ...   # 新增厂商=新增 adapter，不改上层
# 用于：ASR/TTS/LLM 多厂商可插拔（"新增一个 tech 模式"）。
```

### Pipeline / Template Method（固化多阶段流程）
```
class Pipeline:
    stages = [Understand(), Extract(), Decide(), Compile(), Validate()]
    def run(self, x):
        for s in self.stages: x = s.process(x)   # 单向、每阶段可独立测试
        return x
# 用于：AI Agent 分层管道、消息处理全流程。
```

### Factory（消除散落的具体类构造）
```
def make_client(kind): return {"http": HttpClient, "grpc": GrpcClient}[kind]()
# 用于：按配置切换实现，便于测试替身注入。
```

### Chain of Responsibility（可插拔的处理链/兜底）
```
rule_result = rule_handler.handle(x)
return rule_result if rule_result.confident else llm_fallback.handle(x)
# 用于：规则优先 + LLM 兜底。
```

## 反模式提醒
- ❌ 为"将来可能扩展"预埋大量抽象（YAGNI）。
- ❌ 一次引入多个模式导致新结构比旧的更难懂。
- ✅ 每引入一个模式，都要能说清"它消除了哪个具体坏味道"。
