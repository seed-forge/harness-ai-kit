"""loopctl CLI - Loop lifecycle management.

Implements F-006 (loop-cli-tool).
Commands: init, list, validate, status, history, pause, resume, cancel, doctor, metrics, run.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import click


@click.group()
@click.version_option(version="0.1.0", prog_name="loopctl")
def main() -> None:
    """loopctl - Loop lifecycle management CLI."""


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------

@main.command()
@click.argument("loop_id")
@click.option("--name", default="", help="Human-readable loop name.")
@click.option("--scenario", default="", help="Scenario type (engineering-quality, content-ops, etc.).")
@click.option("--output", "-o", default=".", help="Output directory.")
def init(loop_id: str, name: str, scenario: str, output: str) -> None:
    """Create a new Loop asset from template."""
    out = Path(output) / loop_id
    if out.exists():
        click.echo(f"Error: directory {out} already exists.", err=True)
        sys.exit(1)

    template_dir = Path(__file__).parent.parent.parent / "loops" / "_template"
    if not template_dir.exists():
        # Fallback: create minimal structure
        out.mkdir(parents=True)
        loop_data = {
            "schema_version": "1",
            "id": loop_id,
            "name": name or loop_id,
            "owner": "team",
            "version": "0.1.0",
            "status": "draft",
            "package_type": "loop",
            "summary": f"{name or loop_id} Loop asset.",
            "entry": "LOOP.md",
            "dependencies": [],
            "loop_specific": {
                "maker": {"entry": "LOOP.md", "agent_type": "subagent"},
                "checker": {
                    "entry": "CHECK.md",
                    "agent_type": "subagent",
                    "rubric": {
                        "dimensions": [],
                        "pass_threshold": 0.8,
                    },
                },
                "stop_conditions": {
                    "success": [{"identifier": "rubric_pass", "predicate": "checker_score >= 0.8"}],
                    "failure": [{"identifier": "max_errors", "predicate": "error_count >= 3"}],
                    "budget": [{"identifier": "max_iterations", "predicate": "iteration_count >= 10"}],
                },
            },
        }
        (out / "loop.json").write_text(json.dumps(loop_data, indent=2, ensure_ascii=False), encoding="utf-8")
        (out / "LOOP.md").write_text(f"# {name or loop_id} - Maker Entry\n", encoding="utf-8")
        (out / "CHECK.md").write_text(f"# {name or loop_id} - Checker Entry\n", encoding="utf-8")
        (out / "USAGE.md").write_text(f"# {name or loop_id} - Usage\n", encoding="utf-8")
        (out / "CHANGELOG.md").write_text("# Changelog\n\n## 0.1.0\n\n- Initial draft.\n", encoding="utf-8")
        click.echo(f"Created loop asset: {out}")
        return

    import shutil
    shutil.copytree(str(template_dir), str(out))
    # Update loop.json with provided id/name
    loop_json_path = out / "loop.json"
    if loop_json_path.exists():
        data = json.loads(loop_json_path.read_text(encoding="utf-8"))
        data["id"] = loop_id
        data["name"] = name or loop_id
        loop_json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    click.echo(f"Created loop asset from template: {out}")


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------

@main.command("list")
@click.option("--status", "filter_status", default=None, help="Filter by status.")
@click.option("--json", "as_json", is_flag=True, help="JSON output.")
def list_loops(filter_status: str | None, as_json: bool) -> None:
    """List installed Loop assets."""
    repo_root = _find_repo_root()
    if not repo_root:
        click.echo("Error: not inside a harness-ai-kit repository.", err=True)
        sys.exit(1)

    loops_dir = repo_root / "loops"
    if not loops_dir.exists():
        click.echo("No loops found.")
        return

    loops = []
    for child in sorted(loops_dir.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        loop_json = child / "loop.json"
        if not loop_json.exists():
            continue
        try:
            data = json.loads(loop_json.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if filter_status and data.get("status") != filter_status:
            continue
        loops.append(data)

    if as_json:
        click.echo(json.dumps(loops, indent=2, ensure_ascii=False))
        return

    if not loops:
        click.echo("No loops found matching criteria.")
        return

    click.echo(f"{'ID':<30} {'Name':<30} {'Status':<10} {'Version':<10} {'Risk':<10}")
    click.echo("-" * 90)
    for loop in loops:
        risk = loop.get("loop_specific", {}).get("risk_level", "-")
        click.echo(
            f"{loop.get('id', '?'):<30} "
            f"{loop.get('name', '?'):<30} "
            f"{loop.get('status', '?'):<10} "
            f"{loop.get('version', '?'):<10} "
            f"{risk:<10}"
        )


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------

@main.command()
@click.argument("loop_id")
@click.option("--deep", is_flag=True, help="Deep validation including dependency resolution.")
@click.option("--check-predicates", is_flag=True, help="Validate predicate syntax.")
def validate(loop_id: str, deep: bool, check_predicates: bool) -> None:
    """Validate a loop.json file."""
    repo_root = _find_repo_root()
    if not repo_root:
        click.echo("Error: not inside a harness-ai-kit repository.", err=True)
        sys.exit(1)

    loop_dir = repo_root / "loops" / loop_id
    if not loop_dir.exists():
        click.echo(f"Error: loop '{loop_id}' not found.", err=True)
        sys.exit(1)

    loop_json = loop_dir / "loop.json"
    if not loop_json.exists():
        click.echo(f"Error: loop.json not found in {loop_dir}.", err=True)
        sys.exit(1)

    try:
        from harness_ai_kit.domain.loop_manifest import load_loop_manifest_file
        manifest = load_loop_manifest_file(loop_json)
        click.echo(f"Schema validation: PASS")
        click.echo(f"  id: {manifest.id}")
        click.echo(f"  name: {manifest.name}")
        click.echo(f"  version: {manifest.version}")
        click.echo(f"  package_type: {manifest.package_type}")
        click.echo(f"  risk_level: {manifest.loop_specific.risk_level}")
        click.echo(f"  execution_mode: {manifest.loop_specific.execution_mode}")

        # Validate stop conditions
        manifest.loop_specific.stop_conditions.validate()
        click.echo(f"Stop conditions: PASS")

        # Validate rubric weights
        if manifest.loop_specific.checker.rubric.dimensions:
            manifest.loop_specific.checker.rubric.validate_weights_sum()
            click.echo(f"Rubric weights: PASS")

    except Exception as exc:
        click.echo(f"Schema validation: FAIL", err=True)
        click.echo(f"  {exc}", err=True)
        sys.exit(1)

    # Check companion docs exist
    for doc_name in ["USAGE.md", manifest.entry]:
        doc_path = loop_dir / doc_name
        if doc_path.exists():
            click.echo(f"Companion doc {doc_name}: EXISTS")
        else:
            click.echo(f"Companion doc {doc_name}: MISSING", err=True)

    if check_predicates:
        from harness_ai_kit.domain.loop_contract import validate_predicate, STANDARD_METRICS
        custom_metrics = set(manifest.loop_specific.convergence_metric.__dict__.keys())
        all_conditions = (
            manifest.loop_specific.stop_conditions.success
            + manifest.loop_specific.stop_conditions.failure
            + manifest.loop_specific.stop_conditions.budget
        )
        for cond in all_conditions:
            try:
                validate_predicate(cond.predicate, custom_metrics)
                click.echo(f"Predicate [{cond.identifier}]: VALID")
            except Exception as exc:
                click.echo(f"Predicate [{cond.identifier}]: INVALID - {exc}", err=True)

    click.echo(f"\nValidation complete for '{loop_id}'.")


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

@main.command()
@click.argument("profile_id")
@click.option("--json", "as_json", is_flag=True, help="JSON output.")
def status(profile_id: str, as_json: bool) -> None:
    """Show Loop instance status."""
    state_path = _find_state_file(profile_id)
    if not state_path or not state_path.exists():
        click.echo(f"No state file found for profile '{profile_id}'.")
        return

    from harness_ai_kit.domain.loop_state import load_state
    state = load_state(state_path)
    if state is None:
        click.echo(f"Error: could not load state from {state_path}.", err=True)
        sys.exit(1)

    if as_json:
        click.echo(json.dumps(state.model_dump(mode="json"), indent=2, ensure_ascii=False))
        return

    click.echo(f"Loop: {state.loop_id}")
    click.echo(f"Profile: {state.profile_id}")
    click.echo(f"Status: {state.status.value}")
    click.echo(f"Iteration: {state.current_iteration}")
    click.echo(f"Created: {state.created_at}")
    click.echo(f"Updated: {state.updated_at}")
    if state.last_error:
        click.echo(f"Last Error: {state.last_error}")
    if state.convergence_metrics:
        latest = state.convergence_metrics[-1]
        click.echo(f"Latest Score: {latest.primary_metric}")
        click.echo(f"Latest Verdict: {latest.verdict}")


# ---------------------------------------------------------------------------
# history
# ---------------------------------------------------------------------------

@main.command()
@click.argument("profile_id")
@click.option("--last", default=10, help="Number of recent entries to show.")
@click.option("--verbose", is_flag=True, help="Show iteration details.")
def history(profile_id: str, last: int, verbose: bool) -> None:
    """Show Loop run history."""
    state_path = _find_state_file(profile_id)
    if not state_path or not state_path.exists():
        click.echo(f"No state file found for profile '{profile_id}'.")
        return

    from harness_ai_kit.domain.loop_state import load_state
    state = load_state(state_path)
    if state is None:
        click.echo(f"Error: could not load state.", err=True)
        sys.exit(1)

    metrics = state.convergence_metrics[-last:]
    if not metrics:
        click.echo("No convergence metrics recorded.")
        return

    click.echo(f"{'Iter':<6} {'Score':<8} {'Verdict':<10} {'Trend':<15} {'Timestamp'}")
    click.echo("-" * 60)
    for m in metrics:
        click.echo(
            f"{m.iteration:<6} {m.primary_metric:<8} "
            f"{(m.verdict.value if m.verdict else '-'):<10} "
            f"{(m.trend or '-'):<15} {m.timestamp}"
        )

    if verbose and state.iteration_details:
        click.echo("\n--- Iteration Details ---")
        for iter_key, detail in sorted(state.iteration_details.items()):
            click.echo(f"\nIteration {iter_key}:")
            click.echo(f"  Summary: {detail.maker_summary}")
            click.echo(f"  Files: {', '.join(detail.files_changed)}")
            click.echo(f"  Duration: {detail.duration_seconds}s")


# ---------------------------------------------------------------------------
# pause / resume / cancel
# ---------------------------------------------------------------------------

@main.command()
@click.argument("profile_id")
def pause(profile_id: str) -> None:
    """Pause a running Loop."""
    state_path = _find_state_file(profile_id)
    if not state_path:
        click.echo(f"Error: state file not found for '{profile_id}'.", err=True)
        sys.exit(1)

    from harness_ai_kit.domain.loop_state import load_state, save_state, LoopStatus
    state = load_state(state_path)
    if state is None:
        click.echo("Error: could not load state.", err=True)
        sys.exit(1)
    if state.status != LoopStatus.RUNNING:
        click.echo(f"Error: can only pause running loops, current status: {state.status.value}", err=True)
        sys.exit(1)

    state.status = LoopStatus.PAUSED
    save_state(state, state_path)
    click.echo(f"Loop '{profile_id}' paused.")


@main.command()
@click.argument("profile_id")
def resume(profile_id: str) -> None:
    """Resume a paused Loop."""
    state_path = _find_state_file(profile_id)
    if not state_path:
        click.echo(f"Error: state file not found for '{profile_id}'.", err=True)
        sys.exit(1)

    from harness_ai_kit.domain.loop_state import load_state, save_state, LoopStatus
    state = load_state(state_path)
    if state is None:
        click.echo("Error: could not load state.", err=True)
        sys.exit(1)
    if state.status != LoopStatus.PAUSED:
        click.echo(f"Error: can only resume paused loops, current status: {state.status.value}", err=True)
        sys.exit(1)

    state.status = LoopStatus.RUNNING
    save_state(state, state_path)
    click.echo(f"Loop '{profile_id}' resumed.")


@main.command()
@click.argument("profile_id")
@click.option("--force", is_flag=True, help="Cancel without confirmation.")
def cancel(profile_id: str, force: bool) -> None:
    """Cancel a Loop. Irreversible."""
    if not force:
        click.confirm(f"Cancel loop '{profile_id}'? This is irreversible.", abort=True)

    state_path = _find_state_file(profile_id)
    if not state_path:
        click.echo(f"Error: state file not found for '{profile_id}'.", err=True)
        sys.exit(1)

    from harness_ai_kit.domain.loop_state import load_state, save_state, LoopStatus
    state = load_state(state_path)
    if state is None:
        click.echo("Error: could not load state.", err=True)
        sys.exit(1)

    state.status = LoopStatus.CANCELLED
    save_state(state, state_path)
    click.echo(f"Loop '{profile_id}' cancelled.")


# ---------------------------------------------------------------------------
# doctor
# ---------------------------------------------------------------------------

@main.command()
@click.argument("loop_id")
def doctor(loop_id: str) -> None:
    """Run health checks on a Loop asset."""
    repo_root = _find_repo_root()
    if not repo_root:
        click.echo("Error: not inside a harness-ai-kit repository.", err=True)
        sys.exit(1)

    loop_dir = repo_root / "loops" / loop_id
    if not loop_dir.exists():
        click.echo(f"Error: loop '{loop_id}' not found.", err=True)
        sys.exit(1)

    checks = []

    # Check loop.json exists and is valid
    loop_json = loop_dir / "loop.json"
    if loop_json.exists():
        try:
            from harness_ai_kit.domain.loop_manifest import load_loop_manifest_file
            manifest = load_loop_manifest_file(loop_json)
            checks.append(("loop.json schema", "PASS"))
        except Exception as exc:
            checks.append(("loop.json schema", f"FAIL: {exc}"))
    else:
        checks.append(("loop.json schema", "FAIL: not found"))

    # Check companion docs
    for doc in ["LOOP.md", "CHECK.md", "USAGE.md"]:
        if (loop_dir / doc).exists():
            checks.append((doc, "EXISTS"))
        else:
            checks.append((doc, "MISSING"))

    # Check stop conditions
    if loop_json.exists():
        try:
            manifest = load_loop_manifest_file(loop_json)
            manifest.loop_specific.stop_conditions.validate()
            checks.append(("stop_conditions", "PASS"))
        except Exception as exc:
            checks.append(("stop_conditions", f"FAIL: {exc}"))

    click.echo(f"Doctor check for '{loop_id}':")
    for name, result in checks:
        status_icon = "OK" if result in ("PASS", "EXISTS") else "FAIL"
        click.echo(f"  [{status_icon}] {name}: {result}")


# ---------------------------------------------------------------------------
# metrics
# ---------------------------------------------------------------------------

@main.command()
@click.argument("loop_id")
@click.option("--dimension", default=None, help="Specific dimension to inspect.")
def metrics(loop_id: str, dimension: str | None) -> None:
    """Show Loop quality metrics."""
    click.echo(f"Metrics for '{loop_id}':")
    click.echo("  (Metrics aggregation requires a running loop instance with convergence data.)")
    click.echo("  Use 'loopctl status <profile-id>' to view current metrics.")


# ---------------------------------------------------------------------------
# extract
# ---------------------------------------------------------------------------

@main.command()
@click.argument("wfs_id")
@click.option("--dry-run", is_flag=True, help="Only score the session without generating assets.")
@click.option("--force", is_flag=True, help="Generate assets even if score is below threshold.")
@click.option("--loop-id", default=None, help="Override the generated loop ID.")
@click.option("--output", "-o", default=None, help="Output directory (default: loops/{id}/draft/).")
@click.option("--skill-dir", default=None, help="Explicit skill directory to read metadata from.")
def extract(wfs_id: str, dry_run: bool, force: bool, loop_id: str | None, output: str | None, skill_dir: str | None) -> None:
    """Extract loop assets from a completed workflow session."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    from loopctl.loop_extract_cmd import command_extract
    code = command_extract(
        wfs_id,
        dry_run=dry_run,
        force=force,
        loop_id=loop_id,
        output=output,
        skill_dir=skill_dir,
        echo=click.echo,
    )
    if code != 0:
        sys.exit(code)


# ---------------------------------------------------------------------------
# promote
# ---------------------------------------------------------------------------

@main.command()
@click.argument("loop_id")
@click.option("--force", is_flag=True, help="Promote even if validation fails.")
def promote(loop_id: str, force: bool) -> None:
    """Promote a draft loop to official status."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    from loopctl.loop_extract_cmd import command_promote
    code = command_promote(
        loop_id,
        force=force,
        echo=click.echo,
    )
    if code != 0:
        sys.exit(code)


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------

@main.command()
@click.argument("loop_id")
@click.option("--loop-dir", default=None, help="Explicit loop asset directory.")
@click.option("--profile", default=None, help="Profile config file path.")
@click.option("--state-file", default=None, help="Explicit state file path.")
@click.option("--dry-run", is_flag=True, help="Validate loop.json and show config without executing.")
@click.option("--resume", is_flag=True, help="Resume from existing state if found.")
@click.option("--background", is_flag=True, help="Run loop in background (detached).")
def run(
    loop_id: str,
    loop_dir: str | None,
    profile: str | None,
    state_file: str | None,
    dry_run: bool,
    resume: bool,
    background: bool,
) -> None:
    """Execute a Loop asset (Maker-Checker iterations)."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    from harness_ai_kit.commands.loop_run import command_run, run_in_background

    if background:
        code = run_in_background(
            loop_id=loop_id,
            loop_dir=loop_dir,
            profile_path=profile,
            state_file=state_file,
            resume=resume,
        )
    else:
        code = command_run(
            loop_id=loop_id,
            loop_dir=loop_dir,
            profile_path=profile,
            state_file=state_file,
            dry_run=dry_run,
            resume=resume,
            background=False,
            echo=click.echo,
        )

    if code != 0:
        sys.exit(code)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_repo_root() -> Path | None:
    """Walk up to find a harness-ai-kit.yml or catalog.md."""
    current = Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / "harness-ai-kit.yml").exists() or (parent / "catalog.md").exists():
            return parent
    return None


def _find_state_file(profile_id: str) -> Path | None:
    """Try to find the state file for a profile."""
    repo_root = _find_repo_root()
    if not repo_root:
        return None
    # Check common locations
    candidates = [
        repo_root / ".workflow" / "loops" / f"{profile_id}.json",
        repo_root / ".loops" / f"{profile_id}.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]  # Return default path even if not exists


if __name__ == "__main__":
    main()