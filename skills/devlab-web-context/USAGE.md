# USAGE — devlab-web-context

## 前置条件

- 在**目标前端项目根目录**下工作（不是本 kit 仓库）。
- 项目至少含 `package.json`（前端框架 deps）。
- 已读本技能的 `SKILL.md`（双模式入口 + 画像契约）。

## 可直接复制的中文 Prompt

```
按 devlab-web-context 模式 B 执行：
- Identify Scope：项目根 + 子应用清单 + 理解目的
- Build Minimal Context：读 profiles/<type>.md + REFERENCE-WEB-RULES.md，最小信号扫描
- Confidence Check：逐键核对 confidence（confirmed 需 evidence）
- 不足 → Deepen Context；认知偏差 → Re-understand
- 产出 .harness/devlab/context/<project>-web-context.yaml（7 固定键，契约见 SKILL.md）
约束：事实源纪律（禁编造）、HD-W2 脱敏、todo 保留骨架不省略。
```

> 模式 A（被 bootstrap 委托）无需单独触发；模式 B 见下方 Prompt。

## 验证（交付前）

- 画像文件存在且 7 个固定键齐全（`tech_stack` / `dev_server` / `module_registry` / `dev_proxy` / `routing` / `build_deploy` / `component_library`）。
- 每条 `confidence` ∈ {confirmed, inferred, todo}；`confirmed` 有 evidence。
- 敏感信息零落盘：`grep -rniE "password|passwd|secret|token" .harness/devlab/context/` 应为空（环境变量引用除外）。
- `overall_confidence` 与各条一致（无 confirmed 却标 low 的矛盾）。

## 常见失败

| 失败 | 处置 |
|------|------|
| 子类型判定模糊 | HD-W1：向用户确认一句，默认 vue-microfrontend |
| 子应用漏扫（monorepo） | 回退 Identify Scope，按 workspaces 逐个进入可运行子包 |
| 画像键缺 todo 骨架 | 补回未识别键为 todo，不省略小节 |
| 与后端条目混写 | 边界见 REFERENCE-WEB-RULES"与后端 context 的边界"，代理目标只写网关层 |
