# AI 服务测试分级隔离模式（来源：某 NL2DSL 服务，已脱敏）

> 来源：某 NL2DSL 服务（已脱敏）经 devlab-spec-miner 挖掘（2026-08-17，testing 域 6 条 confirmed）。
> 适用：测试天然依赖外部 LLM / 向量库 / 容器的 AI 服务——核心诉求是分级隔离，让「无依赖测试默认全绿、重依赖测试显式选入」。

## 模式总览

```
依赖属性分级（marker） → opt-in 开关（默认跳过） → 环境隔离（fake key / mock_env）
```

## 1. marker 九级分类

在 `pyproject.toml [tool.pytest.ini_options]` 集中声明依赖属性 marker：

```
docker / integration / slow / contract / real_api / e2e / connectivity / property / llm_required
```

- marker 表达的是**运行依赖属性**（需要容器？需要真实 API？需要 LLM 连接？），不是测试类型
- conftest.py 同步注册一遍兜底（防 pyproject 未生效场景）

## 2. 重依赖测试 opt-in 开关

`conftest.py` 三段式：

```python
def pytest_addoption(parser):          # ① 声明 --run-docker / --run-integration 开关
def pytest_configure(config):          # ② 注册 marker
def pytest_collection_modifyitems(config, items):
    # ③ 未传开关 → collection 阶段对带 marker 的用例批量 add_marker(skip)
```

**效果**：默认 `pytest` 只跑离线单测；CI 分层流水线按阶段显式传开关（单测 → --run-docker → --run-integration）。

## 3. 假密钥注入

`[tool.pytest_env]` 注入 fake API key（如 `OPENAI_API_KEY=sk-fake-...`）：

- 不依赖真实 LLM 的用例可离线跑，凭据缺失不会在 import 期炸掉
- 真要用 LLM 的用例显式打 `llm_required` / `real_api` marker

## 4. 干净环境 fixture

`mock_env` fixture：`patch.dict(os.environ, {}, clear=True)` —— 每用例清空环境变量，防本机 `.env` 泄漏进测试造成「本机绿 CI 红」。

## 5. 全局超时 + 耗时报告

- `timeout = 120`（thread 法）—— AI 用例挂死不拖垮整条流水线
- `addopts = --durations=10` —— 最慢用例可见，重依赖用例膨胀早发现

## 6. 目录镜像

`tests/` 子目录与 `src/` 模块一一对应（如 tests/<app>/ 21 子目录镜像 19 个源码子域），覆盖率归因直接落模块。

## 落地检查清单

- [ ] pyproject 集中声明 marker，conftest 双注册
- [ ] docker/integration 默认 skip，开关 opt-in
- [ ] fake key 注入 + llm_required 显式标注
- [ ] mock_env fixture 清环境
- [ ] 全局 timeout + durations 报告
- [ ] tests 目录镜像 src 结构

**实证锚点**：来源项目 `pyproject.toml:143-164`、`tests/conftest.py:14-58`。

## 延伸：Agent 测试的 L0-L4 分层（指针）

本模式是 **L0 确定性单测** 的落地形态（marker 分级 + opt-in 开关 + 环境隔离）。多步 Agent 的完整测试分层
（L1 轨迹评测 / L2 输出评测 / L3 生产回归 / L4 安全+成本护栏）由 `devlab-eval-driven-agent` 承载——
其「L0-L4 分层评测矩阵」与本模式衔接；agent 项目的测试路由见 `devlab-test-onboard` 场景矩阵
（「AI Agent / LLM 应用」档）。
