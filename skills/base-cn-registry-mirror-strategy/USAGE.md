# base-cn-registry-mirror-strategy Usage

## When To Use

- 编写或审查 `Dockerfile`、CI 流水线，需要在国内网络下稳定、可重复地拉取基础镜像与语言包。
- 需要把「Docker Hub / apt / apk / npm / PyPI / Maven Central」的加速策略收敛成一套团队口径，而不是每次临时搜索。

## Inputs

- 目标栈：基镜像是 Debian 系还是 Alpine；语言是 Node、Python、JVM（Maven/Gradle）、Go 中的哪些组合。
- 构建环境：本机 `docker build`、公司 CI、Kaniko、BuildKit 隔离构建等（影响是否能用 BuildKit `RUN --mount=type=secret` 等能力）。
- 组织约束：是否已有内网 Nexus / Harbor / 统一代理（若有，应覆盖本 skill 中的公共候选）。

## Output

- 明确三层中每一层应配置什么（见 `SKILL.md`）。
- 可直接粘贴的 `ARG` / `ENV` / `RUN` 片段（见 `references/REFERENCE-MIRROR-RECIPES.md`）。
- 维护说明：如何季度巡检镜像可用性、如何做回退。

## 可直接复制的中文 Prompt

```text
请按 harness-ai-kit 技能 `base-cn-registry-mirror-strategy` 处理：
基镜像：<debian:bookworm-slim | alpine:3.xx | 其他>
语言栈：<node | python | maven | gradle | go | 组合>
构建环境：<本地 docker | GitHub Actions | Woodpecker/Kaniko | 其他>
组织制品库：<有则写 Nexus/Harbor URL；无则写「仅用公共镜像」>

输出：分层策略表 + 建议的 ARG 默认值 + 对应 Dockerfile 片段 + CI 侧需要注入的环境变量清单。
```

## Fast Path

1. 读 `SKILL.md` 的分层决策表。
2. 打开 `references/REFERENCE-MIRROR-RECIPES.md` 复制对应片段。
3. 将默认 URL 换成团队内网文档中的「单一事实源」。
