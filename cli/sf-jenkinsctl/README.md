# jenkinsctl

Jenkins 运维 CLI：基于官方 jenkins-cli.jar 封装，扩展官方不支持的能力。

## 能力范围

| 命令组 | 功能 | 实现方式 |
|--------|------|---------|
| `status` | Jenkins 状态概览 | REST API |
| `version` | CLI + Jenkins 版本 | Python + REST API |
| `doctor` | 环境完整性诊断 | Python |
| `passthrough` | 透传 jenkins-cli.jar | java -jar |
| `credential` | 凭据管理（增删改查） | credentials.xml |
| `tool` | 工具链管理（安装/列表/验证） | .tools_env/ + config.xml |
| `plugin` | 插件管理（安装/搜索/更新） | REST API |
| `config` | 配置管理（读写/备份/恢复） | config.xml |
| `user` | 用户管理（增删/token） | REST API |
| `job` | Job/Folder 管理 | jenkins-cli.jar + REST API |
| `sharedlib` | Shared Library 管理 | config.xml |
| `notify` | 通知管理（测试 webhook） | curl |

## 安装

```bash
pip install sf-jenkinsctl
```

## 配置

在 `~/.harness-ai-kit/config.yaml` 中声明：

```yaml
assets:
  jenkinsctl:
    jenkins_url: https://jenkins.example.invalid
    jenkins_user: admin
    jenkins_api_token: <your-api-token>
    jenkins_container: jenkins-2.x
```

## 快速使用

```bash
# 查看 Jenkins 状态
jenkinsctl status

# 环境诊断
jenkinsctl doctor

# 透传官方 CLI 命令
jenkinsctl passthrough list-jobs
```
