# Team Branch Strategy Reference

## 策略选择矩阵

| 项目类型 | 推荐策略 | 默认分支 | PR 要求 | CI 要求 |
|----------|----------|----------|---------|---------|
| 个人工具/脚本 | Trunk-based | main | 无 | 可选 |
| CLI / Skill / 正式项目 | GitHub Flow | main | 必须 | 必须 |
| 多人协作 / 生产服务 | Git Flow | main + develop | 必须 | 必须 |
| 文档/知识库 | Trunk-based | main | 可选 | 无 |

## Trunk-based（轻量）

适用于个人工具、脚本仓库、知识笔记等：

```
main:  A → B → C → D (直接 push)
```

- 直接 push 到 main，无需 PR
- 仍遵循 Conventional Commits
- 适合变更频率高、影响范围小的项目

## GitHub Flow（标准）

适用于 CLI 工具、Skill 资产、正式项目：

```
main:    A → B → C →──────────── M (merge)
feature:            C → D → E → P (PR)
```

步骤：
1. `git checkout -b feature/TICKET-123-description`
2. 开发 + atomic commits
3. `git push -u origin HEAD`
4. 创建 PR（Gitea: `tea pr create`）
5. CI green + review → merge
6. 删除 feature 分支

## Git Flow（完整）

适用于多人协作、生产服务、需要版本管理的项目：

```
main:     A →───────────────── M (release merge)
develop:  A → B → C → D → E → F
feature:        C → c1 → c2 → merge to develop
release:                    E → r1 → r2 → merge to main + develop
hotfix:   A → h1 (from main) → merge to main + develop
```

## 团队仓库分类

| 仓库 | 策略 | 说明 |
|------|------|------|
| 02-工程工作空间 | Trunk-based | 工作空间级别，变更频繁 |
| fleet-platform | GitHub Flow | 控制仓，必须 PR + review |
| harness-ai-kit skills | GitHub Flow | PR + CI gate → publish |
| Team 应用仓库 | GitHub Flow | PR + CI + ansible deploy |
| 个人脚本/工具 | Trunk-based | 轻量管理 |

## 分支命名规范

### 正确格式

```
feature/TICKET-123-description    # 新功能
fix/TICKET-456-bug-name           # 修复
release/1.2.0                     # 发布分支
hotfix/1.2.1-security-patch       # 紧急修复
docs/update-skill-guide           # 文档
refactor/simplify-auth-flow       # 重构
```

### 反模式（来自踩坑纠正）

| ❌ 错误 | ✅ 正确 | 理由 |
|--------|--------|------|
| `dev/xxx` | `feature/xxx` | `dev/` 前缀语义模糊，AI 常误用 |
| `my-feature` | `feature/my-feature` | 缺少类型前缀，无法一眼识别意图 |
| `update` | `fix/xxx` | 无类型 + 无上下文 |
| `test-branch` | `test/xxx` | 使用连字符而非斜杠，不符合规范 |
| `WIP` | `feature/xxx` | 不应出现在远程历史中 |

## 分支清理

- PR merge 后**立即删除**远程 feature 分支
- 定期清理已合并的本地分支：`git branch --merged main | grep -v main | xargs git branch -d`
- stale 分支（>30 天未更新）应归档或删除
