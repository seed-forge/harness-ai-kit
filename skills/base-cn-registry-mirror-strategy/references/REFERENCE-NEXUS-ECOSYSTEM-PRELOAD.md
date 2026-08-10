# Nexus 全生态私服与预热策略

Homelab / Worklab 在 **Kaniko + Woodpecker + 跨境网络** 场景下，仅把构建指向国内公共镜像站（npmmirror、阿里云 Maven、goproxy.cn 等）往往**仍然很慢**：流量仍走公网 CDN、大制品重复下载、镜像站同步滞后、且经 Clash 代理时易 502/超时。

本 reference 规定：**凡 Nexus 能承接的依赖生态，只要存在「大依赖」或构建关键路径依赖，默认建议 `Nexus group（统一入口）+ hosted 预热`，而不是单独依赖 CN 公网代理镜像。**

与 `base-cn-registry-mirror-strategy` 分层对应：

| 层级 | 本策略中的角色 |
|------|----------------|
| L2 公共 CN 镜像 | 无 Nexus 时的**应急默认**、小依赖、一次性本地构建 |
| L3 Nexus group | **CI / deploy-apps 的单一事实源**（构建只认 group URL） |
| L3 hosted 预热 | 大依赖、镜像站滞后、官方独占 index（如 PyTorch）的**显式落盘** |

PyPI 已按此模式落地，见 `Homelab/ansible-control/artifacts/nexus-pypi/README.md`；其它生态应对齐同一抽象，而不是各写各的「换阿里云」。

---

## 1. 何时必须建议 Nexus + 预热

满足**任一**条件，助手在审查 Dockerfile / CI / 依赖清单时应主动建议 **group + manifest 预热**（而非仅改 `ARG` 为 npmmirror / aliyun）：

1. **单制品体积大**：例如 pip wheel / Maven jar / npm tarball / Go module zip 常态 **> 50 MiB**，或单次构建某生态下载 **> 5 分钟**。
2. **版本钉死且重复拉取**：同一 `==` / lockfile 版本被多个 `deploy-apps`、多分支 CI、多阶段 `RUN` 反复下载。
3. **公共镜像站不可靠**：`preflight` 在 group/proxy 上查不到 pinned 版本，或已知镜像站比 upstream 慢数日（PyPI 已有先例）。
4. **构建在代理环境**：Woodpecker/Kaniko 配 `HTTP_PROXY` 时，外网 registry 常比内网 Nexus **更慢或更脆**；`NO_PROXY` 须含 `nexus.example.example.com`（及 `.base.example.com`）。
5. **官方独占源**：如 `download.pytorch.org`、部分 npm scope、企业私有 BOM——应进 **专用 hosted**，由 group 聚合，而不是让每次构建直连外网。

以下情况可暂用 **仅 group（靠 proxy 被动缓存）** 或 L2 公共镜像，**不必**先 hosted：

- 依赖体积小、数量多、版本随 upstream 漂移快，且构建时间可接受。
- 仅本地一次性 `docker build`，无团队复用需求。

---

## 2. Nexus 三件套（各生态通用）

| 组件 | 作用 | 构建侧只连谁 |
|------|------|----------------|
| **proxy** | 代理 upstream（PyPI.org、npmjs、Maven Central、proxy.golang.org…），首次请求落盘缓存 | 不直连（由 group 暴露） |
| **hosted** | 预热上传的「确定存在」制品（twine、mvn deploy、npm publish、Go module upload） | 不直连 |
| **group** | 统一入口：hosted 优先，再 proxy | **是** — `PIP_INDEX_URL`、`.npmrc`、`settings.xml` mirror、`GOPROXY` 等 |

预热工作流（与 PyPI `cache` / `hosted` 一致）：

| 策略 | 适用 | 动作 |
|------|------|------|
| **cache** | pinned 版本已在 group simple/index 可见 | 在 <host-01> 经 group 执行 `pip download` / `mvn dependency:get` 等，填满 proxy 缓存 |
| **hosted** | 镜像站滞后、仅 upstream 有、或需专用 hosted 仓 | 从 upstream 拉取 → 上传到 `*-hosted-*` → 经 group 校验 |

每个应用或技术栈维护一份 **manifest profile**（命名建议：`<stack>-<py|node|java|go>-<brief>.conf`），由 Ansible playbook 或受控脚本执行，**禁止**在 Kaniko 构建阶段临时从外网拉百 MB 制品「碰运气」。

---

## 3. 分生态建议（Nexus 可承接部分）

基址示例：`http://nexus.example.example.com:19010`（内网解析；构建 `no_proxy` 必含该主机名）。

| 生态 | 构建消费端配置 | group 入口形态（需在 Nexus 配置） | 预热手段（hosted 优先时） | Homelab 现状（2026-05） |
|------|----------------|-----------------------------------|---------------------------|-------------------------|
| **pip / uv** | `PIP_INDEX_URL`、`PIP_TRUSTED_HOST`；`uv pip` 同 index | `.../repository/pypi-group-repository-all/simple/` | `nexus_pypi_wheels_sync` + `artifacts/nexus-pypi/manifests/*.conf` | **已落地**（voice-pro、moneyprinter、video-analyzer 等） |
| **npm / pnpm** | `.npmrc` `registry=`、`NPM_CONFIG_REGISTRY`；避免构建期 `corepack` 拉 npmjs | `.../repository/npm-group/`（命名以 Nexus 为准） | `npm pack` / `pnpm fetch` → hosted；或 CI `cache` 经 group 拉一次 | 部分仓仍 **npmmirror**（如 newsnow）；**待** group + profile |
| **Maven** | `~/.m2/settings.xml` `<mirror>` 指向 group | `.../repository/maven-public/` 或自建 `maven-group` | `mvn -q dependency:go-offline` + deploy 到 hosted；或 group cache | 文档默认 **阿里云**；**待** manifest + playbook |
| **Gradle** | `settings.gradle` / `init.gradle` → 同一 Maven group | 同上 | 同上 + `./gradlew dependencies` 预热 | **待** |
| **Go modules** | `GOPROXY=https://nexus.../repository/go-group/` | Nexus Go proxy（或 raw + 元数据，按实例配置） | `go mod download` @ pinned → upload hosted / 暖 proxy | 文档默认 **goproxy.cn**；**待** |
| **Docker 基础镜像** | `FROM harbor.base...` | Harbor（常与 Nexus 并列，非同一 daemon） | `skopeo copy` / Harbor proxy cache；大镜像预 pull 到 Harbor | Harbor + Kaniko；与语言源**解耦** |
| **apt / apk** | Dockerfile `sed` 换源 | Nexus raw/proxy（若已配）或 **L2 阿里云** | 一般**不**按包预热；大 deb 可考虑 private mirror | deploy-apps 多内联 **mirrors.aliyun** |
| **raw（skill/cli）** | HTTP GET index | `raw-hosted-skill`、`raw-hosted-cli` | `ai-kit publish` 流程 | **已用于** ai-kit |

**原则**：表中「待」项在 review `deploy-apps` 或新 Java/Node/Go 服务时，应优先排期 **group URL + manifest**，而不是再扩写一条「换 npmmirror / aliyun」的 Dockerfile。

---

## 4. 与「仅 CN 公网镜像」的对比

| 维度 | CN 公网镜像（L2） | Nexus group + hosted 预热（L3） |
|------|-------------------|----------------------------------|
| 路径 | 仍依赖公网 CDN | 构建机 → 内网 Nexus（`no_proxy`） |
| 大 wheel/jar | 每次 CI 可能重复拉 | hosted 一次，group 多次命中 |
| 版本钉死 | 镜像站可能缺包 | preflight + hosted 保证存在 |
| 代理环境 | 易 502/SSL 问题 | 走内网，与 Harbor/Gitea 同域 |
| 维护成本 | 低，但不可控 | manifest + playbook，可审计、可回滚 |

**结论**：CN 镜像写进 `ARG` 默认值适合「没有 Nexus」的模板；**Homelab `deploy-apps` + Woodpecker 标准路径**应把默认值改为 **Nexus group**，大依赖用 **manifest 预热** 补齐。

---

## 5. 助手执行清单（审查构建时）

1. 识别栈：pip / npm / Maven / Gradle / Go / 组合。
2. 从 lockfile、`requirements*.txt`、`package-lock`/`pnpm-lock`、`go.sum` 标出 **>50MiB 或构建瓶颈** 依赖。
3. 若 Nexus 有对应 group：**建议** Dockerfile/CI 默认 `*_URL` → group，并 `trusted-host` / `no_proxy` 对齐。
4. 若 pinned 大依赖：**建议** 新增或扩展 manifest profile，引用（或复制）`nexus_pypi_wheels_sync` 模式；其它生态 playbook 命名建议 `nexus_<ecosystem>_preload`（实现可后置，策略先统一）。
5. 若仅小依赖、无 CI 复用：可保留 L2 CN 镜像，但注明「非 deploy-apps 标准路径」。
6. 输出变更说明时写清：**group URL、manifest 名、preflight/start 命令、回退**（去掉 build-arg 后的行为）。

---

## 6. 相关仓库路径

| 用途 | 路径 |
|------|------|
| PyPI 预热 playbook | `Homelab/ansible-control/playbooks/nexus_pypi_wheels_sync.yml` |
| PyPI manifests | `Homelab/ansible-control/artifacts/nexus-pypi/manifests/` |
| deploy-apps 示例 | `Homelab/gitea-repos/deploy-apps/*-deploy/prepare-upstream.sh`、`.woodpecker.yml` `no_proxy` |
| 公共换源片段（L2） | `base-cn-registry-mirror-strategy/references/REFERENCE-MIRROR-RECIPES.md` |
| 出站代理 | `homelab-worklab-ops/references/REFERENCE-HOMELAB-OUTBOUND-HTTP-PROXY.md` |

---

## 7. 后续实现优先级（建议）

1. **P0**：`deploy-apps` 扫描 — 列出各仓生态 + 大依赖 + 是否已用 Nexus group。
2. **P1**：npm — newsnow 等 Node 仓从 npmmirror 迁到 Nexus group；补 `npm-*` manifest 模板。
3. **P1**：Maven/Gradle — 首个 Java 构建仓的 `settings.xml` + `maven-group` manifest。
4. **P2**：Go — `GOPROXY` group + 模块预热 playbook。
5. **P2**：统一 reference `REFERENCE-DEPLOY-APPS-BUILD-STANDARD.md`（与 Woodpecker 分诊并列）。

本文件为**策略与决策**事实源；具体 Nexus 仓库名以 `<your-server>01` Nexus UI / 运维台账为准，配置变更时同步更新上表「group 入口」列。
