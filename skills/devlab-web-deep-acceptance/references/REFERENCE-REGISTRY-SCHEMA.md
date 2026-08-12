# REFERENCE-REGISTRY-SCHEMA — registry 模式与回写规范

> registry 是整个体系的唯一事实源。本文档定义 schema、回写工程约束与多会话协作协议。

## 一、registry/<module>.yaml — 功能点唯一事实源

```yaml
module: account-manage
app: SystemManage                       # 前端一级 APP 锚点（routers 目录名）
app_path: OperatorManage/AccountManage  # 仅子域粒度模块需要（一级 APP 内视图路径）
name: 账号管理
backend_mappers:                        # precheck 输入：后端 mapper/SQL 目录（相对 test/e2e 或绝对）
  - ../../<repo>/<service>/src/main/resources/mapper
pages:
  - id: account-list
    name: 账号列表页
    route: "#/systemManage/operatorManage/accountManage"
    data_requirement: { min_rows: 3 }     # 造数输入（造数工厂读）
    features:
      - id: al-l3-create                  # 页面缩写前缀，模块内全局唯一
        name: 新增账号
        level: L3
        priority: P0
        steps: 左树选机构→点新增→填 AUTOTEST_ 工号→保存
        expect: 成功提示；列表可查到
        # 执行注：关键事实回写在此（等价替换/造数命令/豁免依据/假成功注记），下轮会话直接受益
        status: pass                      # todo | pass | fail | blocked
        last_run: 2026-07-26
        reason: 数据类——缺XX，解锁命令：node tools/xxx.js   # blocked/fail 必填
```

### 关键规范

1. **feature id 模块内全局唯一，多页模块带页面缩写前缀**（如 `ov-l1-load/dp-l3-archive-verify`）：
   执行器按 `cases/<module>/<feature-id>.case.js` 映射，跨页重复 id 会互相覆盖用例文件
   且 `--case` 无法定位。
2. **registry 声明顺序即执行顺序**；破坏性用例移到依赖它的用例之后并加"执行顺序约束"注释。
3. **模块粒度 = 执行/认领单元**（一次可跑完、一人可认领），产品语义靠 `app:` 锚点挂接，
   **禁止为对齐前端一级 APP 做物理合并**——合并的代价：feature id 跨页冲突互相串写、
   巨模块不可并行认领且一轮跑数小时、cases/reports/factory 历史资产全部断链；
   且前端一级模块本身有漂移（空壳目录、生成产物错指），不是稳定语义锚点。
   新模块 id 命名 `<app-kebab>-<域>`（如 system-management-log），存量不改名（增量迁移）。
4. **注释是经验载体**：`# 执行注:` 承载等价替换说明、造数命令、豁免依据、假成功注记——
   这是回写必须保注释的根本原因。

## 二、registry/modules.yaml — 模块总账（认领制）

```yaml
modules:
  - id: account-manage
    name: 账号管理
    app: SystemManage
    route: "#/systemManage/operatorManage/accountManage"   # 线索不是事实，以 dry-run 实测为准
    priority: P0
    status: done                  # todo | in_progress | done | blocked | out_of_scope
    claimed_by: null              # session-<YYYYMMDD>-<字母>
    claimed_at: null
    progress: "13/15 pass, 2 blocked(冻结态消耗品)"
    report: reports/account-manage/SUMMARY.md
    note: ""                      # out_of_scope 必须写依据
```

- **范围核验**：验证范围以实际部署的后端服务为准（如 `git ls-files -- '<模块>/pom.xml'`）。
  前端有入口但后端未部署 → `out_of_scope` + note 依据，释放认领。
- **out_of_scope 模块已有结果保留**，但 SUMMARY 注明"范围外，FAIL 不计缺陷"。

## 三、回写工程约束（执行器侧，血泪教训固化）

1. **文本级精准替换，禁用 yaml.dump 全量重写**——dump 会丢失全部 `# 执行注:` 注释。
   实现：逐行扫描定位 `status:`/`last_run:`/`reason:` 行，就地替换/插入/删除
   （注意 splice 位移后重扫定位）。
2. **reason 单引号 YAML 标量**：内部单引号翻倍转义（`'`→`''`）；**换行压平**
   （`replace(/\s*\n\s*/g,' ')`——JS 错误栈多行文案注入会炸 "multiline key"）；
   截断 300 字符。
3. **写回前 js-yaml 回验**：解析失败则放弃落盘 + 醒目 banner 告警（registry 与 SUMMARY
   将失同步，必须手工补回写）+ 退出码 3。
4. **总账 modules.yaml 收尾严格校验**（只读告警不阻断）：手工编辑易产生尾逗号/多行/
   嵌套引号，炸掉审计工具。
5. **SUMMARY 从回写后的 registry 终态聚合**：本轮执行过的用本轮结果，未执行的用终态
   补齐并注明来源（否则 --all 跳过的 blocked 与默认模式跳过的 pass 会缺行）。
6. **批量改 registry 的脚本写完必须 js-yaml 回验**；reason 含冒号必须加引号；
   脚本改文件用 `\r?$` 容忍 CRLF/LF 混行。

## 四、多会话协作协议

### 认领

1. 挑 `status: todo` 且 `claimed_by: null` 的模块（优先 P0），写 `claimed_by: session-<日期>-<字母>` +
   `claimed_at`，status 改 in_progress。**commit 即抢占确认**（注意：commit 通常由用户执行，
   会话只改文件并请用户确认提交；冲突时后提交者换模块）。
2. 认领的 route 是线索不是事实，以 `--dry-run` 实际导航和路由源码为准。

### 僵尸接管

`claimed_at` 超 **2 天**未更新 → 视为僵尸认领，其他会话可强制接管（覆写 claimed_by 并注明接管）。

### 接管前残留检查（强制）

认领模块（尤其自认为"新/未入总账"的）先查前会话残留，避免覆盖既有工作：

1. `ls cases/<module>/` 与 `ls -la registry/<module>.yaml`——已存在则本次是**接管**而非新建；
2. `git status --short cases/<module>/ registry/<module>.yaml`——看有无未提交草稿；
3. 既有 `_helpers.js`/`.case.js` **禁止整文件覆盖**，用增量编辑，或先 git stash/备份；
4. 总账无该模块但 registry/cases 已存在，属跨上下文/并发会话状态错位——以当前实际内容
   为准补登总账，不重头再来。

### 编号防撞（并行会话血泪）

- pending-issues 新问题一律**模块前缀编号** `问题 <模块缩写>-<序号>`（如 `问题 DC-1`），
  禁止全局纯数字编号（"看最大号+1"已致多次撞车）；
- 用例/registry 中引用问题号的时机：BLOCKED 抛错文案优先写"问题短语"，编号在收尾
  pending-issues 定稿后再统一注入——避免编号变更传染到用例源码→报告→registry 三层；
- 陷阱清单追加：追加前**重新 grep 取当前最大号**（别用会话早期读到的旧快照），
  新编号=最大号+1，落盘后复验无重号；一次只加自己实证过的，附模块名+日期。

### 会话生命周期 SOP

```
1. 认领：读 modules.yaml → 认领 → 请用户 commit 抢占
2. 盘点：读路由+视图源码逐按钮盘点 → 写 registry/<module>.yaml → 用户抽查确认
3. 预检：node run.js <module> --precheck（缺表/缺列/缺函数/方言 → 预判 blocked）
4. 备数：node run.js <module> --seed（造数工厂）
5. 执行：--dry-run 先行 → 逐功能点 L1→L4；探索一次即固化 .case.js
6. 处置：FAIL 走五分类路由，修复最小化——修完只重跑该功能点+同页受影响功能点
7. 收尾：--audit 三对齐审计 → 四对齐核数（registry × SUMMARY × 总账 progress）
        → 一次性探针移入 tools/_archive/（结论固化后，mv 不删）
        → SUMMARY 生成 → 总账回写并释放 → 请用户 commit
```

## 五、dashboard 全局视图

`node tools/dashboard.js` 从 modules.yaml + 全部 registry 聚合生成 `docs/e2e-dashboard.md`
（自动生成，**勿手改**）：模块状态矩阵 + 功能点状态统计（pass/fail/blocked/todo 计数与占比）
+ blocked 根因分布（数据/环境/权限/后端缺陷四类）。

## 六、并行会话基线数据竞态

非测试前缀基线（字典/阈值/schema）的探测结论**有时效性**：

- 基线类补数的"检查"结论不能沿用会话早期快照，**临执行前必须复测**；
- seed 脚本一律幂等（先 count 预检，已存在即跳过）；
- 探测结果异常翻转时先查 modules.yaml 同域 in_progress 会话，主键段主动避让；
- 基线修复跨模块受益且无法带测试前缀，超出常规造数约定，**须用户确认后执行**
  （可追溯性用"整键此前 0 行/desc 标记"替代前缀），作废的 seed 部分在 SQL 归档头注明
  "vN 作废原因"留证。
