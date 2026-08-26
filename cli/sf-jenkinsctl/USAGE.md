# jenkinsctl — 使用指南

## 概述

Jenkins 运维 CLI，封装官方 jenkins-cli.jar 并扩展凭据、工具链、插件等管理能力。

## 前置条件

- Python >= 3.10
- Jenkins 实例可达（HTTP）
- Jenkins API Token（在 Jenkins UI → User → Configure → API Token 生成）

## 安装

标准安装：

```bash
pip install sf-jenkinsctl
```

uv 用户：

```bash
uv tool install sf-jenkinsctl
```

注意事项：

- PyPI distribution 名称为 `sf-jenkinsctl`，命令入口仍为 `jenkinsctl`，以避免与公网同名包混淆。
- 源码安装：必须在 `cli/jenkinsctl/` 目录内执行 `pip install .`，且 pip>=21.3 / setuptools>=61（旧版本不识别 PEP 621 元数据，会装成 UNKNOWN-0.0.0）；禁止在 harness-ai-kit 仓库根目录执行（根目录是另一个包的 pyproject.toml）。

## 配置

在 `~/.harness-ai-kit/config.yaml` 中声明连接信息：

```yaml
assets:
  jenkinsctl:
    jenkins_url: https://jenkins.example.invalid
    jenkins_user: admin
    jenkins_api_token: <your-api-token>
    jenkins_container: jenkins-2.x
    jenkins_home: /var/jenkins_home
```

敏感字段（`jenkins_api_token`）不设默认值，必须显式配置。

## 可直接复制的中文 Prompt

```text
用 jenkinsctl 检查一下 Jenkins 环境是否完整
```

```text
用 jenkinsctl 看看当前有哪些凭据
```

```text
用 jenkinsctl 安装 JDK 8 到 Jenkins 工具链
```

## 命令参考

| 命令 | 说明 |
|------|------|
| `jenkinsctl status` | Jenkins 状态概览（版本/节点/队列/磁盘） |
| `jenkinsctl version` | CLI + Jenkins 版本信息 |
| `jenkinsctl doctor` | 环境完整性诊断 |
| `jenkinsctl passthrough <args>` | 透传参数给 jenkins-cli.jar |
| `jenkinsctl credential list` | 列出凭据（脱敏） |
| `jenkinsctl tool list` | 列出已安装工具 |
| `jenkinsctl plugin list` | 列出已安装插件 |
| `jenkinsctl job list` | 列出所有 Job |
| `jenkinsctl job build <name>` | 触发构建 |
| `jenkinsctl job console <name>` | 查看控制台日志（tail） |
| `jenkinsctl build list <job>` | 列出构建历史 |
| `jenkinsctl build info <job> <N>` | 构建详情（状态/参数/变更） |
| `jenkinsctl build log <job> <N>` | 控制台日志（--full/-o 导出） |
