# Team PR Workflow Reference

## PR 创建规范

### 标题格式
PR 标题遵循 Conventional Commits 格式：

```
feat(cli): add shared-resources command
fix(infra-ingress-ops): OpenResty reload 后未验证证书链
docs(harness-ai-kit-forge): 补充 MCP Server 创建示例
```

### PR Body 结构

```markdown
## 变更摘要
<一句话说明这个 PR 做了什么>

## 影响范围
- <受影响的模块/组件>

## 变更详情
- <具体变更 1>
- <具体变更 2>

## 测试/验证
- <验证方式>

## Checklist
- [ ] Conventional Commits 格式
- [ ] 同一 PR 内语言一致（中文或英文）
- [ ] 无遗留 TODO
- [ ] 测试通过
- [ ] 文档更新（如适用）
```

## Merge 前检查清单

1. **CI green** — 所有 pipeline 通过
2. **Review threads resolved** — 所有评审意见已处理
3. **Rebased** — 与目标分支无冲突
4. **Atomic commits** — 每个 commit 做一件事
5. **No WIP commits** — 历史干净可 review

## Merge 策略

| 场景 | 策略 | 理由 |
|------|------|------|
| 标准 feature PR | merge commit | 保留完整历史和原子性 |
| 小修小补 | rebase (fast-forward) | 线性历史更干净 |
| 实验性分支合入 | squash | 压缩为一个有意义的 commit |

**默认使用 merge commit**，除非有明确理由选择 squash。

## Self-Review 流程

在请求他人 review 之前，先 self-review：

1. `git diff main...HEAD` — 检查全部变更
2. 确认无调试代码、临时无注释、硬编码凭据
3. 确认 commit 消息清晰可读
4. 确认 CI pipeline 已通过
