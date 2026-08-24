# CLI 资产创建规范

## 何时选择 CLI

- 需要命令行工具封装可参数化的操作序列
- 操作可脚本化、可管道组合
- 反复手动执行的 `ssh + 命令` 模式

## CLI 目录结构

```
cli/{id}/
├── cli.json          # 元数据：id, version, install_type, package_name
├── pyproject.toml    # Python 包配置（python-package 类型）
├── {package}/        # Python 源码包
│   ├── __init__.py
│   └── ...
├── USAGE.md          # 用法说明
├── CHANGELOG.md      # 版本历史
└── tests/            # 可选：单元测试
```

## cli.json 必填字段

| 字段 | 说明 | 示例 |
|------|------|------|
| `id` | 唯一标识 | `"devlab-tool-codegen"` |
| `name` | 人类可读名称 | `"代码生成器"` |
| `version` | 语义化版本 | `"0.1.0"` |
| `status` | `draft` / `trial` / `stable` | `"trial"` |
| `package_type` | 固定 `"cli"` | `"cli"` |
| `install_type` | `python-package` / `binary-release` | `"python-package"` |
| `package_name` | PyPI 包名 | `"devlab-codegen"` |
| `summary` | 一句话说明 | — |

## CLI 命名规范

- ID：`devlab-tool-{function}`（如 `devlab-tool-codegen`）
- PyPI 包名：`{function-short-name}`（如 `devlab-codegen`）
- 命令名：短小精悍，可用缩写（如 `codegen`）

## 配套 Skill 要求

每个 CLI 必须有配套的使用说明 Skill（`*-usage`），因为：
- CLI 提供执行能力
- Skill 提供使用时机和上下文判断
- AI agent 通过 Skill 知道"什么时候该用这个 CLI"

## 发布流程

```
1. bump version in cli.json + pyproject.toml
2. harness-ai-kit publish-cli {id}
3. 回读 Nexus index.json 确认 latest_version
4. 本地 pip install --upgrade 验证
```
