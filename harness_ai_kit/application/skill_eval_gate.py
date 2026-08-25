"""publish-skill eval gate: 发布前跑 skill 评测，防质量回归。

Why this module exists
----------------------
``publish-skill`` 目前只做静态门禁（frontmatter / manifest / cli.json）。
有评测套件（``evals/skills/<skill-id>/suite.yaml``）的 skill 在发布时如果
没有质量门槛，AI 改动可能导致行为回归而无人察觉。本模块在 frontmatter
门禁之后接入 evalctl 的 skill-eval + diff：

1. 跑候选：``evalctl skill-eval --skill <id> --mode with-skill --repeat 1
   --run-name skill-eval-publish-<id>-<ts>``（落 Langfuse dataset run）
2. 取 pass@1：``evalctl report --format json`` 解析 ``skill-eval.pass``
3. 回归比对：给 ``--eval-baseline <run>`` 时 ``evalctl diff --format json``
   统计回归用例数（跌幅超过阈值的 case 数）

门禁判定：

- 有套件 + evalctl 可用：pass@1 < ``min_pass`` 或回归用例数 > 0 → block
- 有套件但未给 baseline：只做 pass@1 下限（首版发布不要求历史基线）
- 无套件 / 无 evalctl / ``--skip-eval-gate``：不阻止，输出说明

设计约束：

- 不引入 Langfuse 直连（复用 evalctl 作为唯一评测执行入口，避免双实现）
- 子进程超时给足（5 case × codex exec ≈ 25 分钟量级）
- dry-run 只报告计划，不真正执行 codex exec
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

EVAL_DIMS = "used,pass,methodology"
EVAL_SCORE_PREFIX = "skill-eval"
DEFAULT_MIN_PASS = 0.8
DEFAULT_MAX_DROP_PP = 10.0
GATE_TIMEOUT_SECONDS = 3600


@dataclass(frozen=True)
class EvalGateResult:
    """门禁判定结果。

    decision: pass | block | skip | no-suite | dry-run
    """

    decision: str
    message: str
    candidate_run: str | None = None
    pass_rate: float | None = None
    regressions: int | None = None


def eval_suite_path(repo_root: Path, skill_id: str) -> Path:
    """评测套件路径：``<repo_root>/evals/skills/<skill_id>/suite.yaml``。"""
    return repo_root / "evals" / "skills" / skill_id / "suite.yaml"


def resolve_evalctl() -> str | None:
    """在 PATH 上解析 evalctl 可执行文件。"""
    return shutil.which("evalctl")
def _run_evalctl(
    evalctl: str,
    args: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """执行 evalctl 子命令，捕获输出，超时门禁时间。"""
    return subprocess.run(
        [evalctl, *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=GATE_TIMEOUT_SECONDS,
    )


def _parse_report_pass_rate(stdout: str) -> float | None:
    """从 evalctl report --format json 提取 pass@1（skill-eval.pass 均值）。"""
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    cases = payload.get("cases", {})
    pass_key = f"{EVAL_SCORE_PREFIX}.pass"
    values = [
        v
        for row in cases.values()
        if isinstance((v := row.get(pass_key)), (int, float))
    ]
    if not values:
        return None
    return sum(values) / len(values)


def _count_regressions(stdout: str) -> int | None:
    """从 evalctl diff --format json 统计回归用例数；解析失败返回 None。"""
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    regressions = payload.get("regressions")
    if not isinstance(regressions, list):
        return None
    return len(regressions)


def run_skill_eval_gate(
    *,
    repo_root: Path,
    skill_id: str,
    baseline_run: str | None = None,
    min_pass: float = DEFAULT_MIN_PASS,
    max_drop_pp: float = DEFAULT_MAX_DROP_PP,
    skip: bool = False,
    dry_run: bool = False,
    evalctl: str | None = None,
    env: dict[str, str] | None = None,
) -> EvalGateResult:
    """执行 publish-skill eval 门禁（详见模块 docstring）。"""
    if skip:
        return EvalGateResult(
            "skip", "eval 门禁未启用（默认跳过；用 --run-eval-gate 显式启用）"
        )
    suite = eval_suite_path(repo_root, skill_id)
    if not suite.exists():
        rel = suite.relative_to(repo_root)
        return EvalGateResult("no-suite", f"无评测套件 {rel}，跳过 eval 门禁")

    evalctl_bin = evalctl or resolve_evalctl()
    if evalctl_bin is None:
        if baseline_run:
            return EvalGateResult(
                "block",
                "publish-skill eval gate: 指定了 --eval-baseline 但未找到 evalctl"
                " 可执行文件（请 pip install -e cli/evalctl）",
            )
        return EvalGateResult(
            "skip", "未找到 evalctl，跳过 eval 门禁（安装 evalctl 后自动启用）"
        )
    if dry_run:
        return EvalGateResult(
            "dry-run",
            f"将执行: evalctl skill-eval --skill {skill_id} --mode with-skill"
            f" --repeat 1（候选 run 落库）+ evalctl report/diff 判定"
            + (f"，baseline={baseline_run}" if baseline_run else "，无 baseline 仅 pass@1 下限"),
        )
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    candidate_run = f"skill-eval-publish-{skill_id}-{ts}"
    dataset = f"skill-eval-{skill_id}"

    # 1) 跑候选并落库（with-skill / repeat 1）
    run = _run_evalctl(
        evalctl_bin,
        [
            "skill-eval",
            "--skill", skill_id,
            "--mode", "with-skill",
            "--repeat", "1",
            "--run-name", candidate_run,
        ],
        cwd=repo_root,
        env=env,
    )
    if run.returncode != 0:
        tail = (run.stdout + run.stderr)[-2000:]
        return EvalGateResult(
            "block",
            f"eval 门禁: skill-eval 执行失败（exit {run.returncode}），候选 run"
            f" {candidate_run} 未完成。\n{tail}",
            candidate_run=candidate_run,
        )

    # 2) pass@1 下限
    report = _run_evalctl(
        evalctl_bin,
        [
            "report",
            "--dataset", dataset,
            "--run-name", candidate_run,
            "--format", "json",
            "--dims", EVAL_DIMS,
            "--score-prefix", EVAL_SCORE_PREFIX,
        ],
        cwd=repo_root,
        env=env,
    )
    pass_rate = _parse_report_pass_rate(report.stdout)
    if pass_rate is None:
        return EvalGateResult(
            "block",
            f"eval 门禁: evalctl report 输出无法解析（{dataset}/{candidate_run}）",
            candidate_run=candidate_run,
        )
    if pass_rate < min_pass:
        return EvalGateResult(
            "block",
            f"eval 门禁未通过: pass@1={pass_rate:.2f} < 下限 {min_pass:.2f}"
            f"（dataset {dataset}，候选 run {candidate_run}）",
            candidate_run=candidate_run,
            pass_rate=pass_rate,
        )

    # 3) 回归比对（可选 baseline）
    regressions = 0
    if baseline_run:
        diff = _run_evalctl(
            evalctl_bin,
            [
                "diff",
                "--dataset", dataset,
                "--baseline", baseline_run,
                "--candidate", candidate_run,
                "--format", "json",
                "--dims", EVAL_DIMS,
                "--score-prefix", EVAL_SCORE_PREFIX,
                "--threshold", f"{max_drop_pp / 100.0:.3f}",
            ],
            cwd=repo_root,
            env=env,
        )
        regressions = _count_regressions(diff.stdout)
        if regressions is None:
            return EvalGateResult(
                "block",
                f"eval 门禁: evalctl diff 输出无法解析（{dataset}: {baseline_run} →"
                f" {candidate_run}）",
                candidate_run=candidate_run,
                pass_rate=pass_rate,
            )
        if regressions > 0:
            return EvalGateResult(
                "block",
                f"eval 门禁未通过: {regressions} 个 case 相对基线 {baseline_run}"
                f" 回归（跌幅阈值 {max_drop_pp:g}pp）",
                candidate_run=candidate_run,
                pass_rate=pass_rate,
                regressions=regressions,
            )

    return EvalGateResult(
        "pass",
        f"pass@1={pass_rate:.2f}" + (f"，相对基线 {baseline_run} 无回归" if baseline_run else "（无基线，仅下限校验）"),
        candidate_run=candidate_run,
        pass_rate=pass_rate,
        regressions=regressions,
    )
