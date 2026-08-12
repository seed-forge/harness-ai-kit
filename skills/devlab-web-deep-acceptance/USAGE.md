# devlab-web-deep-acceptance — 使用指南

## 何时使用

- 接手一个**存量 Web 系统**（已有大量页面/接口，质量未知），需要系统性深度验收；
- 需要沉淀**可重放的回归资产**（不是一次性点检，而是 registry + 用例 + 报告 + dashboard）；
- 多会话/多人并行铺开多模块测试，需要认领协调与状态总账。

**不适用**：绿field 新项目从零生成 E2E 用例（用 `devlab-web-test-e2e`）；
纯后端 API 测试（用 `devlab-srv-test-api`）。

## 快速开始（新项目落地 6 步）

```bash
# 1. 建工程骨架
mkdir -p test/e2e && cd test/e2e
# 从本技能 scripts/ 拷贝执行器与框架库
cp -r <skill>/scripts/* .
npm i playwright js-yaml && npx playwright install chromium

# 2. 配环境（唯一需要改的文件）
cp e2e.config.example.js e2e.config.js
# 改 baseUrl / 登录选择器与凭据 / businessApiPattern / dbServerUrl / 豁免表

# 3. Phase 0-1：画像盘点 + registry 建模
# 按 SKILL.md Phase 0/1 读前端路由与视图源码，写 registry/modules.yaml 与 registry/<module>.yaml
# （模板在 templates/），用户抽查确认

# 4. Phase 2：预检
node run.js <module> --precheck

# 5. Phase 3-4：dry-run 先行，然后分级执行
node run.js <module> --dry-run
node run.js <module>

# 6. Phase 5-6：收尾
node run.js <module> --audit
node tools/dashboard.js   # 全局视图
```

## 可直接复制的中文 Prompt

**通用认领**：

```
认领一个模块做深度验收测试，L1-L4 全深度，数据不足就造数，发现问题按五分类修复，
盘点后等我抽查 registry 再开测。
```

**指定模块**：

```
认领「XX模块」做深度验收：先跑 --precheck 静态扫该模块 mapper SQL；盘点后等我抽查；
数据不足造数（只动 AUTOTEST_ 前缀）；发现问题直接修复但不 commit；日志类空数据按
入库断链剖析数据链。
```

## 关键纪律（摘自实战教训）

1. registry 是唯一事实源——根因/解锁命令写 registry 的 reason 与 `# 执行注:`，**不要手写 SUMMARY**（会被覆盖）；
2. HTTP 200 ≠ 业务成功——依赖查询结果的断言必须解析响应体（六态分诊）；
3. 探索一次即固化 `.case.js`——收尾 `--audit` 会查"pass 但无用例"；
4. 同一功能点修复 ≤3 轮，超过登记 pending-issues 标 blocked，不死磕；
5. 环境故障停下上报等恢复，禁止会话自行重启共享服务；
6. 遇阻先查 `references/REFERENCE-PITFALLS.md`（72 条实战陷阱）。
