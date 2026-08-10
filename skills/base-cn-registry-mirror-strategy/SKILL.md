---
name: base-cn-registry-mirror-strategy
description: 国内镜像源与代理分层策略（Docker / Debian / Alpine / Node / Python / Maven / Gradle / Go），用于 Dockerfile 与 CI 的可维护加速。
---

# base-cn-registry-mirror-strategy

## 用途

在**中国大陆网络**或跨境不稳定场景下，为容器镜像与语言包拉取提供**一套可维护的分层策略**：先定「谁负责加速」（宿主机 Docker、CI 注入、`Dockerfile` 内显式换源），再按栈选用**可替换的默认候选 URL**，避免每次临时拼命令。

适用于：

- 编写、审查或重构 `Dockerfile`、多阶段构建
- 配置 CI（含 Kaniko、BuildKit、自托管 Runner）
- 与团队内 Nexus / Harbor 策略对齐前的**公共默认基线**

## 输入

- 基础镜像家族：Debian/Ubuntu 系、Alpine，或其它（需单独评估）
- 语言与工具：Node/npm、Python/pip、Maven、Gradle、Go modules
- 构建环境：本地、云 CI、是否允许访问外网公共镜像
- 组织是否提供：Docker Registry 镜像、PyPI/npm/Maven 代理、HTTP(S)_PROXY

## 输出

- **分层策略表**：每一层配置什么、何时用、与安全的边界
- **默认候选**：阿里云、清华 TUNA、中科大等可互换的「默认占位」，团队应收敛为单一事实源
- **可复制片段**：见 `references/REFERENCE-MIRROR-RECIPES.md`

## 核心原则（必读）

1. **单一事实源**：对外发布的 `Dockerfile` 里用 `ARG` 暴露镜像 URL，默认值可以指向公共镜像；团队内部在 CI 或 `docker build --build-arg` 中注入组织制品库地址，避免在仓库里硬编码易失效的第三方 URL 且无出口替换。
2. **公共镜像 ≠ 长期承诺**：域名、路径、同步延迟会变；本 skill 提供**维护节奏**（建议每季度巡检 + 出问题时切换 `ARG`），不保证某一第三方站点永久可用。
3. **合规优先**：若公司有「仅允许内网源」或审计要求，以安全与合规为准，本 skill 中的公共地址仅作开发/Homelab 基线参考。
4. **Docker Hub 与语言源解耦**：`docker pull` / `FROM` 慢，与 `apt`、`npm`、`pip` 慢是不同链路；**不要**只配一种就以为全覆盖。
5. **大依赖优先 Nexus 预热，而非仅 CN 公网镜像**：凡 Nexus 能承接的生态（pip、npm、Maven、Gradle、Go 等），若存在大体积或 CI 关键路径依赖，应建议 **Nexus group 统一入口 + hosted/manifest 预热**；仅把 `ARG` 改成 npmmirror / 阿里云 / goproxy.cn 仍可能很慢（公网 CDN、代理、镜像站滞后）。决策表与分生态清单见 `references/REFERENCE-NEXUS-ECOSYSTEM-PRELOAD.md`。

## 分层策略

| 层级 | 解决什么问题 | 典型手段 | 备注 |
|------|----------------|----------|------|
| L0 宿主机 / Runner | `docker pull`、`FROM` 拉取慢 | `/etc/docker/daemon.json` 的 `registry-mirrors`；或企业内 Harbor 前置缓存 | 影响**构建机**拉基础镜像，不写入 `Dockerfile` |
| L1 CI 环境变量 | 构建阶段内的网络工具与 CLI | `HTTP_PROXY`/`HTTPS_PROXY`/`NO_PROXY`；`DOCKER_BUILDKIT=1` | Homelab 宿主机默认代理见 `homelab-worklab-ops/references/REFERENCE-HOMELAB-OUTBOUND-HTTP-PROXY.md` |
| L2 Dockerfile `ARG` | 可重复、可审计的换源 | 各语言 `*_MIRROR` / `*_URL` 默认 + build-arg 覆盖 | **推荐**作为团队统一模式 |
| L3 仅内网发布 | 出网受限 | `FROM` 与包源全部改为内网 registry / Nexus group | 与 `infra-source-image-pipeline-ops` 等流水线 skill 配合 |
| L3b Nexus 预热 | 大 wheel/jar、钉死版本、镜像站缺包 | hosted 上传 + group 消费；manifest + Ansible（PyPI 已示范） | **Homelab deploy-apps / Woodpecker 标准路径**；见 `REFERENCE-NEXUS-ECOSYSTEM-PRELOAD.md` |

## 默认候选（占位，可被 ARG 覆盖）

以下仅为**常见公共加速**（L2 应急或小依赖）；**Homelab CI 与大依赖场景默认应改为 Nexus group**，勿把本段当作 deploy-apps 终态。团队应在内网文档固定一套；多选一即可，不必同时使用。

- **Debian apt**：`https://mirrors.aliyun.com/debian`（主）/ `https://mirrors.tuna.tsinghua.edu.cn/debian`（备）
- **Alpine apk**：`https://mirrors.aliyun.com/alpine/`（注意版本目录 `v3.xx/main` 等）
- **npm**：`https://registry.npmmirror.com`
- **pip**：`https://pypi.tuna.tsinghua.edu.cn/simple` 或 `https://mirrors.aliyun.com/pypi/simple/`
- **Maven Central 聚合**：`https://maven.aliyun.com/repository/public`
- **Gradle 插件与依赖**：优先通过 `settings.gradle` / `init.gradle` 指到组织 Nexus；公共可用阿里云 Maven 聚合作临时替代（见参考文档）
- **Go**：`GOPROXY=https://goproxy.cn,direct`

## 工作流（助手执行顺序）

1. 确认栈与基镜像；若属 Homelab `deploy-apps`、Woodpecker/Kaniko 或复用构建：先读 `REFERENCE-NEXUS-ECOSYSTEM-PRELOAD.md`，标出大依赖是否需 manifest 预热。
2. 选择 L0～L3b 中**最小必要集**（能内网 Nexus group 则优先 L3/L3b，L2 仅作无 Nexus 时的默认）。
3. 在 `Dockerfile` 顶部声明 `ARG`（带合理默认值），`RUN` 中只引用变量，避免魔法字符串散落；group URL 默认值优先于公网镜像站。
4. 在 CI 中注入 `build-arg` 或环境变量，与 `NO_PROXY`（含 `nexus.example.example.com`、`.base.example.com`）一并核对。
5. 产出变更说明：group/manifest 名、preflight/预热命令、构建示例、回退方式。

## 推荐输出格式

执行完毕后输出极简回执：**状态**（✅ 成功 / ⚠️ 部分成功 / ❌ 失败）+ **关键结果**（1-2 行，如操作对象、产出位置、下一步）。无需强制套用大表格。


## 约束

- 不在 skill 中嵌入任何密钥、token、私有内网 URL（由项目或 CI secret 注入）。
- 修改官方基础镜像内源文件前，确认许可证与镜像维护方约定；多阶段构建中**构建阶段**换源、**运行阶段**尽量不再保留构建机上的敏感配置。
- 若与 `infra-woodpecker-pipeline-ops` 等技能同时出现：`FROM` 指向 Harbor 基座镜像时，**语言包源**仍可按本 skill 单独配置。

## 专题引用

- **Nexus 全生态私服与预热（大依赖必看）**：`references/REFERENCE-NEXUS-ECOSYSTEM-PRELOAD.md`
- **Homelab 执行编排**（manifest、波次 B、Harbor warm、Woodpecker inspect）：`infra-artifact-readiness-ops`
- 长篇可复制片段与命令：`references/REFERENCE-MIRROR-RECIPES.md`（在 `ai-kit` 仓库内路径为 `skills/base-cn-registry-mirror-strategy/references/REFERENCE-MIRROR-RECIPES.md`；若以「02-工程工作空间」为根，则为 `工程规范/ai-kit/skills/base-cn-registry-mirror-strategy/references/REFERENCE-MIRROR-RECIPES.md`）
- Homelab 宿主机出站 HTTP 代理（GitHub / Google 等 GFW 站点）：`homelab-worklab-ops/references/REFERENCE-HOMELAB-OUTBOUND-HTTP-PROXY.md`

## 维护建议

- **每季度**：任选一条最小构建（如 `docker build --pull`）验证各 `ARG` 默认仍可用。
- **故障时**：先切备用镜像域名，再评估是否改为组织 Nexus 单一入口。

参考文档：
- references/REFERENCE-README.md
