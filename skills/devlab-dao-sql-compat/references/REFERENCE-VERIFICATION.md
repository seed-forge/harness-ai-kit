# 修复验证方法（三层）

按可用条件从 L1 到 L3 逐层执行；高层不可用时按降级声明模板明确告知用户。

## L1 静态复扫（必做，零依赖）

修复完成后重跑扫描脚本，对比修复前后命中数：

    bash <skill>/scripts/scan-sql-compat.sh --dir <scan_dir> --report <report_path>

判定：
- 目标模块的"被消除方言"命中数应降为 0（或仅剩已标记"需人工复核"的项）
- 其他模块命中数不得增加（防止误改）
- 输出对比表：模块 × (修复前 → 修复后) 命中数

## L2 语法预检（可选，需库连接）

仅当用户通过 L2/L3 配置提供 verify_jdbc_url（或项目内已有 SQL 执行通道，如统一 DB 代理服务）时执行。

- PostgreSQL：`PREPARE chk AS <sql>` 后 `DEALLOCATE chk`；或 `EXPLAIN <sql>`（不执行数据变更）
- Oracle：`EXPLAIN PLAN FOR <sql>`；DML 可包在 `SAVEPOINT` + `ROLLBACK` 中
- MySQL：`PREPARE chk FROM '<sql>'` 后 `DEALLOCATE PREPARE chk`；或 `EXPLAIN <sql>`

范围：只对"结构性重写"清单中的 SQL 逐条预检；参数占位符（#{...}）先替换为同类型字面量样例。

## L3 业务执行验证（用户自行回归）

Skill 不代跑业务：提示用户对修复涉及的接口/页面做回归，并给出涉及的 Mapper 方法清单辅助圈定回归范围。

## 降级声明模板

L2 不可用时，修复记录中必须包含：

> ⚠ 验证降级声明：本次修复仅通过 L1 静态复扫验证（方言命中数对比）。
> 未执行数据库语法预检（未提供库连接）。以下 N 处结构性重写建议在测试环境执行 L2/L3 验证后再上生产：
> （列出文件:行号 + 重写类型）
