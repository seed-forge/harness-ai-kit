from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _strip_terminal_punctuation(text: str) -> str:
    return text.rstrip("。．.！？!?、，,;；:： ")


def _compact_summary(summary: str) -> str:
    text = _strip_terminal_punctuation(_clean_text(summary))
    for prefix in (
        "Task-oriented CLI for ",
        "Task-oriented wrapper CLI for ",
        "Team maintenance CLI for ",
        "Official ",
    ):
        if text.startswith(prefix):
            return _strip_terminal_punctuation(text[len(prefix) :])
    return _strip_terminal_punctuation(text)


def _usage_title(name: str) -> str:
    return f"# {name} Usage"


def _prompt_block(title: str, lines: list[str]) -> list[str]:
    return [f"### {title}", "```text", *lines, "```"]


def _render_lines(
    title: str,
    when: list[str],
    inputs: list[str],
    outputs: list[str],
    prompts: list[list[str]],
    fast_path: list[str],
) -> str:
    prompt_lines: list[str] = []
    for block in prompts:
        if prompt_lines:
            prompt_lines.append("")
        prompt_lines.extend(block)
    blocks = [
        title,
        "",
        "## When To Use",
        *when,
        "",
        "## Inputs",
        *inputs,
        "",
        "## Output",
        *outputs,
        "",
        "## 可直接复制的中文 Prompt",
        *prompt_lines,
        "",
        "## Fast Path",
        *fast_path,
        "",
    ]
    return "\n".join(blocks)


def _render_ai_kit_operator(metadata: Mapping[str, Any]) -> str:
    asset_id = _clean_text(metadata.get("id") or "harness-ai-kit-ops")
    name = _clean_text(metadata.get("name") or metadata.get("id") or "harness-ai-kit-ops")
    entry = _clean_text(metadata.get("entry") or "SKILL.md")
    when = [
        "- Use this skill when you need to operate `harness-ai-kit` from the member side: install, list, show, cat, sync, doctor, create, submit, or upgrade.",
        "- Use it when you need a precise command sequence for runtime or scope decisions, a new-machine bootstrap, or a membership-side troubleshooting step.",
    ]
    inputs = [
        "- Asset type and ID.",
        "- Runtime and scope when installation is involved.",
        "- The current task goal: inspect, install, sync, submit, upgrade, or troubleshoot.",
    ]
    outputs = [
        "- A ready-to-run `harness-ai-kit` command sequence.",
        "- A clear next step if the current runtime is not ready.",
    ]
    prompts = [
        _prompt_block(
            "场景 1：安装或升级资产",
            [
                f"请使用 `{asset_id}` 帮我处理 harness-ai-kit 资产安装或升级。",
                "目标：根据当前项目目录和运行时，给出最合适的 install 或 upgrade 命令。",
                "要求：先检查 runtime、scope、依赖缺口和是否需要同步仓库，再给最终命令。",
                "输出：可直接执行的命令、预期结果、失败时排查点。",
            ],
        ),
        _prompt_block(
            "场景 2：排查资产不可用",
            [
                f"请使用 `{asset_id}` 帮我排查某个 skill 或 companion asset 为什么不可用。",
                "要求：优先检查 doctor、show、cat、lockfile、manifest 和运行时安装位置。",
                "输出：问题定位、修复命令、修复后验证步骤。",
            ],
        ),
    ]
    fast_path = [
        "- Run `harness-ai-kit doctor` first.",
        f"- Use `harness-ai-kit show <type> <id>` or `harness-ai-kit cat <type> <id>` to inspect, then open `{entry}` for the full command flow.",
        "- Read `USAGE.md` before deeper docs when you only need the shortest path.",
    ]
    return _render_lines(_usage_title(name), when, inputs, outputs, prompts, fast_path)


def _render_ai_kit_maintainer(metadata: Mapping[str, Any]) -> str:
    asset_id = _clean_text(metadata.get("id") or "harness-ai-kit-maintainer")
    name = _clean_text(metadata.get("name") or metadata.get("id") or "harness-ai-kit-maintainer")
    entry = _clean_text(metadata.get("entry") or "SKILL.md")
    when = [
        "- Use this skill when you need to change `harness-ai-kit` repository facts: metadata, catalog, templates, validation, or sync behavior.",
        "- Use it when a CLI or asset change must stay aligned across `skill.json`, `cli.json`, `CHANGELOG.md`, `catalog.md`, and the generated docs.",
    ]
    inputs = [
        "- The asset ID or path being changed.",
        "- Current repo state and related files.",
        "- Any CLI, registry, or workspace context that the change touches.",
    ]
    outputs = [
        "- Updated source-of-truth files.",
        "- Validation results and any required version or catalog bumps.",
    ]
    prompts = [
        _prompt_block(
            "场景 1：维护 harness-ai-kit 资产",
            [
                f"请使用 `{asset_id}` 帮我修改 harness-ai-kit 仓库里的资产治理内容。",
                "要求：同步检查 metadata、USAGE.md、CHANGELOG.md、catalog.md、校验规则和安装行为是否一致。",
                "输出：修改方案、实际变更、验证结果、还需要补齐的治理项。",
            ],
        )
    ]
    fast_path = [
        "- Read `README.md`, `catalog.md`, and the relevant asset docs first.",
        f"- Open `{entry}` for the governance workflow, then run validation after edits.",
        "- Keep `USAGE.md` short; put deeper rationale in the main doc or changelog.",
    ]
    return _render_lines(_usage_title(name), when, inputs, outputs, prompts, fast_path)


def _render_ai_kit_cli(metadata: Mapping[str, Any]) -> str:
    name = _clean_text(metadata.get("name") or metadata.get("id") or "harness-ai-kit")
    entry = _clean_text(metadata.get("entry") or "README.md")
    when = [
        f"- Use this CLI when you need the `{name}` command itself for syncing, submitting, releasing, or distributing team assets.",
        "- Use it for repo-level lifecycle work across skills, CLIs, plugins, hooks, subagents, and MCP assets.",
    ]
    inputs = [
        "- Repo root or config path.",
        "- Runtime, scope, asset IDs, and any registry or environment settings.",
        "- The lifecycle action: install, sync, doctor, validate, submit, publish, or release.",
    ]
    outputs = [
        "- Install or sync status, lockfile updates, validation output, or publish results.",
        "- A clear failure message when a dependency or registry state is missing.",
    ]
    prompts = [
        _prompt_block(
            "场景 1：使用 harness-ai-kit CLI",
            [
                f"请使用 `{name}` 这个 CLI 完成当前资产生命周期任务。",
                "要求：先判断应使用 install、sync、doctor、validate、submit、publish 还是 release。",
                "输出：可直接执行的命令、执行顺序、关键注意事项。",
            ],
        )
    ]
    fast_path = [
        "- Run `harness-ai-kit doctor` first.",
        "- Use `harness-ai-kit validate` before submit or release, then read `README.md`, `INSTALL.md`, and `RELEASE.md` for the full flow.",
        f"- Open `{entry}` if you need the source command behavior or packaging details.",
    ]
    return _render_lines(_usage_title(name), when, inputs, outputs, prompts, fast_path)


def _render_deprecated_skill(metadata: Mapping[str, Any], summary: str) -> str:
    asset_id = _clean_text(metadata.get("id") or "deprecated-skill")
    name = _clean_text(metadata.get("name") or metadata.get("id") or "deprecated-skill")
    entry = _clean_text(metadata.get("entry") or "SKILL.md")
    replacement_match = re.search(r"请改用\s*`([^`]+)`", summary)
    replacement = replacement_match.group(1) if replacement_match else ""
    when = [
        f"- Use this skill only as a migration bridge{f' to `{replacement}`' if replacement else ''}.",
        "- Keep it only to preserve the rename or retirement path; do not treat it as the active workflow.",
    ]
    inputs = [
        "- The old asset ID and the replacement target.",
        "- Any migration context from the source repo or runtime install path.",
    ]
    outputs = [
        "- A pointer to the replacement asset and the migration note to follow.",
    ]
    prompts = [
        _prompt_block(
            "场景 1：识别替代资产",
            [
                f"请检查 `{asset_id}` 是否已经废弃，并告诉我应该改用什么资产。",
                "输出：替代资产、迁移原因、下一步操作。",
            ],
        )
    ]
    fast_path = [
        f"- Use `{replacement}` instead for active work." if replacement else "- Use the replacement asset instead for active work.",
        f"- Open `{entry}` only when you need the historical note or deprecation wording.",
    ]
    return _render_lines(_usage_title(name), when, inputs, outputs, prompts, fast_path)


def render_usage_doc(metadata: Mapping[str, Any]) -> str:
    package_type = _clean_text(
        metadata.get("package_type")
        or ("cli" if metadata.get("install_type") else "skill")
    ).lower()
    asset_id = _clean_text(metadata.get("id") or "asset")
    name = _clean_text(metadata.get("name") or asset_id or "Asset")
    summary = _compact_summary(metadata.get("summary") or "")
    entry = _clean_text(metadata.get("entry") or ("SKILL.md" if package_type == "skill" else "README.md"))

    if package_type == "skill" and asset_id == "harness-ai-kit-ops":
        return _render_ai_kit_operator(metadata)
    if package_type == "skill" and asset_id == "harness-ai-kit-maintainer":
        return _render_ai_kit_maintainer(metadata)
    if package_type == "cli" and asset_id == "harness-ai-kit":
        return _render_ai_kit_cli(metadata)
    if package_type == "skill" and ("请改用" in summary or "已废弃" in summary or "deprecated" in summary.lower()):
        return _render_deprecated_skill(metadata, summary)

    if package_type == "cli":
        focus = summary or f"the installed `{name}` command"
        when = [
            f"- Use this CLI when you need the installed `{name}` command.",
            f"- It is {focus}.",
            "- Use it when the task is a command-line lifecycle action, install, or packaging step.",
        ]
        inputs = [
            "- CLI arguments and required environment variables.",
            "- Repo root, config path, runtime, scope, or registry settings when needed.",
            "- Config: read `data/config.defaults.yaml` for key declarations, then `~/.harness-ai-kit/config.yaml` (`assets.<cli-id>` section) for user values.",
        ]
        outputs = [
            "- Command output, installed status, or generated artifacts.",
        ]
        prompts = [
            _prompt_block(
                "场景 1：让 AI 帮你调用 CLI",
                [
                    f"请使用 `{asset_id}` 这个 CLI 处理当前任务。",
                    "先确认命令参数、工作目录、环境变量和作用范围。",
                    "如果依赖没装好，先列出缺口和安装方式。",
                    "输出：可直接执行的命令、预期结果、失败时排查点。",
                ],
            )
        ]
        fast_path = [
            "- Install the CLI first, then read `README.md` and `INSTALL.md` before release work.",
            f"- Open `{entry}` when you need the command entrypoint details.",
            "- Config discovery: `data/config.defaults.yaml` → `~/.harness-ai-kit/config.yaml` (assets section) → ask user for missing required keys.",
        ]
    elif package_type in {"plugin", "hook", "subagent"}:
        focus = summary or f"the workflow described by `{name}`"
        when = [
            f"- Use this {package_type} when the project needs {focus}.",
            "- Use it when the runtime side should pick up a first-class asset that is not a skill.",
        ]
        inputs = [
            "- Trigger context, target asset ID, and project/runtime settings.",
            "- Any install or bundle scope that controls where the asset lands.",
        ]
        outputs = [
            "- A ready asset scaffold, installation result, or runtime-side bundle.",
        ]
        prompts = [
            _prompt_block(
                "场景 1：启用配套资产",
                [
                    f"请使用 `{asset_id}` 这个{package_type}资产支持当前任务。",
                    "先说明它适合什么场景、需要什么输入，以及是否需要先安装或同步。",
                    "输出：最短使用步骤、关键限制、验证方式。",
                ],
            )
        ]
        fast_path = [
            "- Open `README.md` first, then read `USAGE.md` for the shortest path.",
            f"- Read `{entry}` for the main contract if the asset exposes more than one step.",
        ]
    elif package_type == "mcp":
        focus = summary or f"the integration described by `{name}`"
        when = [
            f"- Use this MCP asset when the model needs {focus}.",
            "- Use it when you need a tool-backed integration point rather than a local file-based workflow.",
        ]
        inputs = [
            "- Endpoint, auth, transport, and registry settings.",
            "- Any protocol-specific parameters needed to connect or register the service.",
        ]
        outputs = [
            "- A ready connection or registration result for the target client.",
        ]
        prompts = [
            _prompt_block(
                "场景 1：接入 MCP 资产",
                [
                    f"请帮我接入 `{asset_id}` 这个 MCP 资产。",
                    "先检查连接方式、鉴权、运行时兼容性和是否已经注册。",
                    "输出：接入步骤、验证命令、常见故障排查点。",
                ],
            )
        ]
        fast_path = [
            "- Read the main entry document first, then verify the connection path.",
            f"- Open `{entry}` when the asset defines a custom setup or transport contract.",
        ]
    else:
        focus = summary or f"the workflow described by `{name}`"
        when = [
            f"- Use this skill when you need to {focus}.",
            "- Use it when the task matches the asset's documented workflow and should stay within the skill boundary.",
        ]
        inputs = [
            "- Task goal, source material, and workspace context.",
            "- Any upstream files or examples that the workflow needs to inspect or transform.",
        ]
        outputs = [
            "- The result defined by the main document and its workflow.",
        ]
        prompts = [
            _prompt_block(
                "场景 1：直接调用技能",
                [
                    f"请使用 `{asset_id}` 这个技能处理我的任务。",
                    "输入材料：<在这里补充文件、链接、原始文本或项目背景>。",
                    "目标：<在这里补充你要完成的结果>。",
                    "要求：先判断这个技能是否适合；如果缺少关键输入，先列出缺口；执行时遵循 `SKILL.md` 的规则。",
                    "输出：最终结果、关键检查点、还需要我补充的内容。",
                ],
            )
        ]
        fast_path = [
            f"- Open `{entry}` first.",
            "- Read `EXAMPLE.md` only when the workflow is multi-step, parameter-heavy, or easy to misuse.",
        ]

    return _render_lines(_usage_title(name), when, inputs, outputs, prompts, fast_path)
