# Raw Hosted Asset Retirement

适用于 raw hosted registry 中 Skill、CLI 或其他可寻址资产的正式退役。Git 事实源和 Nexus 分发层必须一起收敛，不能只删除其中一侧。

## 顺序

1. 在 Git 中确认资产已标记 retired/deprecated、替代关系和 catalog 状态已更新。
2. 记录待清理的 archive、metadata、checksum 和 index entry，先做 dry-run 或只读回读。
3. 幂等删除 Nexus 中的 archive 与 metadata；按 registry 实现清理 checksum 和 index entry。
4. 回读旧 URL：预期 404 或明确 retired 响应；回读 index：旧 id 不再可解析，替代 id 的 `latest_version` 正常。
5. 扫描消费侧 lock、manifest、checkout 与各 runtime，确认不存在旧资产的幽灵副本。

## 约束

- 不直接编辑 registry 缓存作为唯一事实源；删除前必须先完成 Git 侧治理。
- 删除动作需要 maintainer 权限，优先使用 CLI 或受控脚本并保留审计记录。
- 发现旧条目重复、索引漂移或删除非幂等时，停止批量清理，先记录差异再处理。
