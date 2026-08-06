# Advanced Git Operations Reference

> 本文件为上游知识指针。完整内容见 netresearch/git-workflow-skill 的 `references/advanced-git.md`。

## 常用操作速查

### Interactive Rebase

```bash
# 重新整理最近 N 个 commit
git rebase -i HEAD~N

# 操作类型：
# pick   — 保留 commit
# squash — 合并到前一个 commit
# reword — 修改 commit message
# drop   — 删除 commit
# edit   — 暂停在该 commit，允许修改
```

### Cherry-pick

```bash
# 挑选单个 commit 到当前分支
git cherry-pick <commit-hash>

# 挑选范围（不含 start）
git cherry-pick <start>..<end>

# 冲突时：解决 → git cherry-pick --continue
# 放弃：git cherry-pick --abort
```

### Bisect（二分查找 bug）

```bash
git bisect start
git bisect bad                # 当前版本有 bug
git bisect good <good-hash>  # 这个版本是好的
# 测试当前 commit → git bisect good/bad
# 完成后 → git bisect reset
```

### Stash

```bash
git stash push -m "description"   # 保存当前修改
git stash list                     # 查看 stash 列表
git stash pop stash@{0}           # 恢复并删除
git stash apply stash@{0}         # 恢复但保留
```

### Worktrees（多分支并行工作）

```bash
# 在新目录 checkout 另一个分支
git worktree add ../my-feature feature/my-feature

# 查看 worktrees
git worktree list

# 清理
git worktree remove ../my-feature
```

### Reflog（恢复丢失的 commit）

```bash
# 查看操作历史
git reflog

# 恢复到某个丢失的 commit
git reset --hard <reflog-hash>

# 或创建新分支指向它
git branch recovery <reflog-hash>
```

## 团队经验

- **bisect 前确保编译通过**：用 `git bisect run <script>` 自动化
- **stash 命名**：总是带 `-m "description"`，方便日后找回
- **worktree 清理**：分支合入后立即 `git worktree remove`，避免目录堆积
- **reflog 是安全网**：几乎所有"丢失"的操作都可以通过 reflog 恢复
