# 镜像与换源片段（可复制）

以下片段假定使用 `ARG` 作为唯一换源入口；团队可将默认值改为内网地址。

**Homelab / Woodpecker / 大依赖**：优先将默认值设为 **Nexus group** 并做 manifest 预热，不要仅依赖本节中的 npmmirror / 阿里云 / goproxy.cn。见同目录 `REFERENCE-NEXUS-ECOSYSTEM-PRELOAD.md`。

---

## 1. Debian / Ubuntu（apt）

在 `Dockerfile` 中（以 Debian bookworm 为例，`DEBIAN_VERSION` 与官方源路径需与实际基础镜像一致）：

```dockerfile
ARG APT_MIRROR=https://mirrors.aliyun.com
RUN sed -i "s@http://deb.debian.org/debian@${APT_MIRROR}/debian@g" /etc/apt/sources.list.d/debian.sources 2>/dev/null || true \
 && sed -i "s@https://deb.debian.org/debian@${APT_MIRROR}/debian@g" /etc/apt/sources.list.d/debian.sources 2>/dev/null || true \
 && sed -i "s@http://deb.debian.org/debian@${APT_MIRROR}/debian@g" /etc/apt/sources.list 2>/dev/null || true \
 && sed -i "s@https://deb.debian.org/debian@${APT_MIRROR}/debian@g" /etc/apt/sources.list 2>/dev/null || true
```

旧版只有 `sources.list` 时，上面后两行已覆盖。若基础镜像是 Ubuntu，将 `deb.debian.org` 替换为 `archive.ubuntu.com` 与 `security.ubuntu.com` 的对应 sed 规则（按镜像内实际行调整）。

---

## 2. Alpine（apk）

```dockerfile
ARG ALPINE_VERSION=3.19
ARG ALPINE_MIRROR=https://mirrors.aliyun.com/alpine
RUN sed -i "s#https://dl-cdn.alpinelinux.org/alpine#${ALPINE_MIRROR}#g" /etc/apk/repositories \
 || sed -i "s#http://dl-cdn.alpinelinux.org/alpine#${ALPINE_MIRROR}#g" /etc/apk/repositories
```

`ALPINE_VERSION` 仅用于文档对齐；仓库路径以 `/etc/apk/repositories` 内实际 `v${major.minor}` 为准。

---

## 3. Node / npm / corepack / pnpm

**npm registry：**

```dockerfile
ARG NPM_CONFIG_REGISTRY=https://registry.npmmirror.com
ENV NPM_CONFIG_REGISTRY=${NPM_CONFIG_REGISTRY}
```

**单次安装（不显式改全局配置）：**

```dockerfile
RUN npm install --registry=${NPM_CONFIG_REGISTRY}
```

**pnpm：**

```dockerfile
ARG NPM_CONFIG_REGISTRY=https://registry.npmmirror.com
RUN corepack enable && npm install -g pnpm --registry=${NPM_CONFIG_REGISTRY} \
 && pnpm config set registry ${NPM_CONFIG_REGISTRY}
```

---

## 4. Python / pip

```dockerfile
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ENV PIP_INDEX_URL=${PIP_INDEX_URL}
ENV PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn
```

单次：

```dockerfile
RUN pip install --no-cache-dir -i "${PIP_INDEX_URL}" some-package
```

使用 `uv` 时优先查 `uv` 官方文档的 index-url 参数，原则同上：用 `ARG` 注入。

---

## 5. Maven

**settings.xml 片段（挂载或 `RUN heredoc` 写入 `/root/.m2/settings.xml`）：**

```xml
<mirrors>
  <mirror>
    <id>aliyunmaven</id>
    <mirrorOf>central</mirrorOf>
    <name>Aliyun Maven</name>
    <url>https://maven.aliyun.com/repository/public</url>
  </mirror>
</mirrors>
```

Dockerfile 中可用 `ARG`：

```dockerfile
ARG MAVEN_MIRROR_URL=https://maven.aliyun.com/repository/public
```

生成 `settings.xml` 时把 `<url>` 设为 `${MAVEN_MIRROR_URL}`（由构建脚本替换或模板渲染）。

---

## 6. Gradle

优先在仓库中提交 `gradle/init.d/mirror.gradle` 或在 `settings.gradle` 里配置 `pluginManagement` / `dependencyResolutionManagement` 指向组织 Nexus。

公共临时方案可将 `MAVEN_MIRROR_URL` 同步为 Gradle 的 mavenCentral 镜像地址（与 Maven 段同一阿里云 URL 常可用，以实际解析为准）。

---

## 7. Go

```dockerfile
ARG GOPROXY=https://goproxy.cn,direct
ENV GOPROXY=${GOPROXY}
```

---

## 8. Docker 守护进程（L0，非 Dockerfile）

构建机 `/etc/docker/daemon.json` 示例（仅说明结构，具体域名以公司或云厂商文档为准）：

```json
{
  "registry-mirrors": [
    "https://<your-mirror-or-hub-proxy>"
  ]
}
```

Kaniko 等无 daemon 场景：依赖上游 `executor` 镜像缓存、Harbor proxy cache，或 CI 侧 `HTTP_PROXY`。

---

## 9. CI 注入示例

```text
docker build \
  --build-arg APT_MIRROR=https://mirrors.aliyun.com \
  --build-arg NPM_CONFIG_REGISTRY=https://registry.npmmirror.com \
  --build-arg PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
  --build-arg MAVEN_MIRROR_URL=https://maven.aliyun.com/repository/public \
  --build-arg GOPROXY=https://goproxy.cn,direct \
  -t myapp:local .
```

---

## 10. NO_PROXY 提示

使用企业 HTTP 代理时，务必将内网域名、Harbor、Nexus、metadata IP 段列入 `NO_PROXY`，否则 apt/npm 可能仍走代理导致失败或更慢。

---

## 11. Homelab 宿主机默认 HTTP 代理（GFW 站点）

在 **<your-server>01 / <your-server>02** 上为 GitHub、Google 等配置 `HTTP_PROXY` 时，**不要**临时猜地址；按主机使用 Clash 混合端口 **7890**：

| 主机 | `HTTP_PROXY` / `HTTPS_PROXY` |
|------|------------------------------|
| <your-server>01 (<host-01>) | `http://clash-112.example.com:7890` |
| <your-server>02 (<host-02>) | `http://clash-119.example.com:7890`（备选 `http://clash.example.com:7890`） |

完整 `NO_PROXY` 基线、compose/CI 落点与验证命令见：

`内部出站代理配置（见团队内部文档，不在本仓库）`
