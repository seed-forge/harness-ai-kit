# CHANGELOG — public-git-workflow-expert-base

## 0.1.3 - 2026-08-14

- frontmatter 规范化：SKILL.md 统一 LF / 无 BOM / 单一 YAML frontmatter 块，修复 AI IDE 加载告警（missing YAML frontmatter delimited by ---）。
## 0.1.2 - 2026-08-06

- 治理清欠：结构合规修复后版本抬升（ref_link、ref_rename:README.md->REFERENCE-README.md、refs）。

## 0.1.1 - 2026-07-23

- fix: environment.system 格式修正为对象数组（CLI 校验要求）
- fix: 社区依赖从 dependencies 改为 extends 声明（CLI 不支持 source_url 解析）

## 0.1.0 - 2026-07-23

- 初始版本。extends netresearch/git-workflow-skill v1.18.8（CC-BY-SA-4.0）
- 上游覆盖：分支策略、Conventional Commits、PR workflow、CI/CD 集成、Git Hooks、高级操作
- 团队叠加层：commit scope 规范、分支策略选择矩阵、Gitea 工作流、Woodpecker/Jenkins CI、Git mirror sync
- 8 个参考文档（references/）
- 定位为 extends 知识基座，供 devlab-git-workflow-expert 等下游技能继承

### 融入 853 会话挖掘踩坑记录

- **合并策略修正**：feature PR 默认 squash merge（来自用户纠正模式）
- **新增 Release & Tag 章节**：`v{major}.{minor}.{patch}` 命名规范 + CI 触发配置
- **新增多仓协同专章**：目录结构、remote 命名、批量操作脚本（GIT-P01，86% 会话涉及）
- **新增分支命名反模式**：`dev/xxx` → `feature/xxx`（AI 常见错误）
- **新增 Pipeline 触发规范**：Git push → Woodpecker/Jenkins 映射 + tag 触发 release（GIT-P02）
- **强化 Gitea-first 规则**：内网镜像优先、`git clone` 不直连 GitHub
