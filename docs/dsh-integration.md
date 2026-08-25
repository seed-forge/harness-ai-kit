# harness-ai-kit × dsh（DeepSeek Harness）集成说明

> 验收基线：dsh `0.1.0-rc.6`（npm）、pnpm ≥10、Node ≥22.19。升级 dsh 前先跑
> `harness-ai-kit doctor dsh` 并重跑冒烟。

## 1. 关系模型（对等集成，非包含）

```
harness-ai-kit（供给侧：CLI + Nexus registry）
  ├─ 内容层：skill 资产经 .agents/skills 原生互通（dsh rank 200/500 扫描，非插件）
  ├─ 能力层：harness-ai-kit-plugin（dsh 插件集合中的一个工具插件，per-profile 选配）
  └─ 供给侧：CLI/registry 独立对等，dsh 只是消费端之一
```

## 2. 安装 dsh（基线）

```bash
npm i -g @deepseek-ai/dsh@0.1.0-rc.6
# 或免全局：npx --yes @deepseek-ai/dsh@0.1.0-rc.6
```

## 3. dsh runtime 支持（技能安装）

```bash
harness-ai-kit install skill <id> --runtime dsh --scope project
# 装入最近项目级 .agents/skills（dsh rank 200 原生扫描，无需额外配置）
harness-ai-kit install skill <id> --runtime dsh --scope global
# 装入 ~/.agents/skills（dsh rank 500 原生扫描）
harness-ai-kit doctor dsh
# dsh/pnpm 版本（基线 0.1.0-rc.6 / >=10）、DSH_HOME、profile 目录
```

### frontmatter 兼容说明

- 技能目录名必须 kebab-case（dsh 只扫 `<name>/SKILL.md` 一层，不支持嵌套）。
- `name` / `description` 必填；description 建议 ≤800 字符（元数据每条约 200-400 tokens，
  总量由「安装数量」控制——按场景安装，勿全量）。
- 噪声/低频技能建议 `disable-model-invocation: true`（仅手动调用）、
  `user-invocable` 控制手动入口。

## 4. plugin 资产类型（dsh 插件发布与安装）

`harness-ai-kit-plugin` 是 plugin 资产类型的第一个实例（宿主 dsh）。

```bash
# 发布（contributor+）：pnpm pack -> raw-hosted-cli/plugins/<id>/<ver>/ + index 条目
harness-ai-kit publish-plugin harness-ai-kit-plugin --dry-run
harness-ai-kit publish-plugin harness-ai-kit-plugin

# 安装（consumer）：registry 下载 tarball -> sha256 校验 -> dsh plugin add -> dump-config 验证
harness-ai-kit install plugin harness-ai-kit-plugin --profile web
# 缺省 profile 取 plugin.json 的 dsh.bundle.default_profile（web）

# 卸载
harness-ai-kit uninstall plugin harness-ai-kit-plugin --profile web
# 或 dsh plugin --profile web remove harness-ai-kit-plugin
```

`harness-ai-kit-plugin` 提供：

- 工具 `harness-ai-kit`：`list` / `search` / `info` / `install` / `doctor`
  （委托本机 CLI；CLI 缺失时只读动作 HTTP 回退直读 registry index）；
- 随包技能 `harness-ai-kit-ops`（精简操作手册，`ctx.skills.register` source: bundled）；
- **虚拟技能**（Phase E）：`ctx.skills.registerProvider` 把 registry 全量技能以
  元数据形式进会话（rank 650，本地技能优先），`get()` 按需拉正文，**不落盘**——
  工作空间零膨胀。

## 5. Token/上下文治理（D11）

1. 技能不进插件（插件只随包 1-2 个核心 ops 技能；其余走原生目录/虚拟技能）。
2. 插件零正文注入：`<available_skills>` 列表长度不因插件膨胀。
3. 元数据瘦身：description ≤800 字符校验；按场景安装（project/global）。
4. frontmatter 治理：disable-model-invocation / user-invocable。
5. 虚拟技能 rank 650：本地（100-600）优先，虚拟只填充空白。

## 6. 升级与回滚

- 升级 dsh：固定版本验收，升级前 `doctor dsh` + 冒烟。
- 插件升级：`harness-ai-kit upgrade plugin harness-ai-kit-plugin --profile web`。
- 回滚：`uninstall plugin`（委托 `dsh plugin remove`，仅 dispose 注册，不删本地技能目录）。

## 7. 已知限制

- 真实发布到 Nexus 需要 registry 凭据（`HARNESS_AI_KIT_REGISTRY_USERNAME/PASSWORD`）。
- dsh 会话内工具调用与虚拟技能列表需要 LLM 配置（headless/web 会话）。
- dsh v0.1 预览接口可能破坏性变更；接口以安装版本为准（doctor 比对基线）。
