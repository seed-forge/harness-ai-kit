"""loopctl extract + promote commands.

Extracts loop assets from completed workflow sessions and promotes
draft loops to official status.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path


def _find_repo_root() -> Path | None:
    """Walk up to find a harness-ai-kit.yml or catalog.md."""
    current = Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / "harness-ai-kit.yml").exists() or (parent / "catalog.md").exists():
            return parent
    return None


def _find_session_dir(wfs_id: str, repo_root: Path) -> Path | None:
    """Find a workflow session directory by WFS ID."""
    active_dir = repo_root / ".workflow" / "active" / wfs_id
    if active_dir.exists():
        return active_dir
    # Check archives
    archives_dir = repo_root / ".workflow" / "archives" / wfs_id
    if archives_dir.exists():
        return archives_dir
    return None


def command_extract(
    wfs_id: str,
    *,
    dry_run: bool = False,
    force: bool = False,
    loop_id: str | None = None,
    output: str | None = None,
    skill_dir: str | None = None,
    echo: callable = print,
) -> int:
    """Extract loop from completed workflow session.

    Returns 0 on success, non-zero on failure.
    """
    from harness_ai_kit.domain.loop_extract import (
        LoopAssetGenerator,
        ValueScorer,
        Recommendation,
    )

    repo_root = _find_repo_root()
    if not repo_root:
        echo("Error: not inside a harness-ai-kit repository.", file=sys.stderr)
        return 1

    # 1. Find session dir
    session_dir = _find_session_dir(wfs_id, repo_root)
    if not session_dir:
        echo(f"Error: session '{wfs_id}' not found in .workflow/active/ or .workflow/archives/.", file=sys.stderr)
        return 1

    echo(f"Found session: {session_dir}")

    # 2. Score session
    scorer = ValueScorer()
    score = scorer.score_session(session_dir)

    echo(f"\nValue Score: {score.total}")
    echo(f"Recommendation: {score.recommendation.value}")
    echo("\nSignals:")
    for sig in score.signals:
        echo(f"  {sig.name}: {sig.score} (confidence={sig.confidence:.2f}) -- {sig.evidence}")

    # 3. Check dry-run first (always allowed regardless of score)
    if dry_run:
        echo("\n[dry-run] Would generate loop assets. Exiting.")
        return 0

    # 4. Check score threshold (only blocks actual generation)
    if score.recommendation == Recommendation.NOT_RECOMMENDED and not force:
        echo(f"\nScore {score.total} is below threshold. Use --force to generate anyway.", file=sys.stderr)
        return 1

    # 5. Determine output directory
    resolved_loop_id = loop_id or wfs_id.lower().replace("wfs-", "").replace("_", "-")
    # Sanitize loop_id to kebab-case
    import re
    resolved_loop_id = re.sub(r"[^a-z0-9]+", "-", resolved_loop_id).strip("-")
    if not resolved_loop_id:
        resolved_loop_id = "extracted-loop"

    if output:
        output_dir = Path(output)
    else:
        output_dir = repo_root / "loops" / resolved_loop_id / "draft"

    # 5. Generate assets
    generator = LoopAssetGenerator()
    skill_path = Path(skill_dir) if skill_dir else None
    try:
        result_dir = generator.generate(
            session_dir=session_dir,
            output_dir=output_dir,
            loop_id=resolved_loop_id,
            skill_dir=skill_path,
        )
    except Exception as exc:
        echo(f"Error generating loop assets: {exc}", file=sys.stderr)
        return 1

    echo(f"\nGenerated loop assets in: {result_dir}")

    # 6. Validate with loopctl validate
    loop_json = result_dir / "loop.json"
    if loop_json.exists():
        try:
            from harness_ai_kit.domain.loop_manifest import load_loop_manifest_file
            manifest = load_loop_manifest_file(loop_json)
            echo(f"\nSchema validation: PASS")
            echo(f"  id: {manifest.id}")
            echo(f"  name: {manifest.name}")
            echo(f"  risk_level: {manifest.loop_specific.risk_level}")

            manifest.loop_specific.stop_conditions.validate()
            echo("Stop conditions: PASS")

            if manifest.loop_specific.checker.rubric.dimensions:
                manifest.loop_specific.checker.rubric.validate_weights_sum()
                echo("Rubric weights: PASS")

        except Exception as exc:
            echo(f"\nSchema validation: FAIL -- {exc}", file=sys.stderr)
            return 1

    echo(f"\nExtraction complete for '{wfs_id}' -> '{resolved_loop_id}'.")
    echo(f"Draft location: {result_dir}")
    echo(f"\nNext steps:")
    echo(f"  1. Review and edit the generated assets")
    echo(f"  2. Run: loopctl promote {resolved_loop_id}")
    return 0


def command_promote(
    loop_id: str,
    *,
    force: bool = False,
    echo: callable = print,
) -> int:
    """Promote draft loop to official.

    Moves loops/{loop_id}/draft/ to loops/{loop_id}/ and validates.
    Returns 0 on success, non-zero on failure.
    """
    repo_root = _find_repo_root()
    if not repo_root:
        echo("Error: not inside a harness-ai-kit repository.", file=sys.stderr)
        return 1

    draft_dir = repo_root / "loops" / loop_id / "draft"
    official_dir = repo_root / "loops" / loop_id

    if not draft_dir.exists():
        echo(f"Error: draft directory not found: {draft_dir}", file=sys.stderr)
        echo(f"Expected: loops/{loop_id}/draft/", file=sys.stderr)
        return 1

    loop_json = draft_dir / "loop.json"
    if not loop_json.exists():
        echo(f"Error: loop.json not found in draft directory.", file=sys.stderr)
        return 1

    # 1. Validate draft
    try:
        from harness_ai_kit.domain.loop_manifest import load_loop_manifest_file
        manifest = load_loop_manifest_file(loop_json)
        echo(f"Draft validation: PASS")
        echo(f"  id: {manifest.id}")
        echo(f"  name: {manifest.name}")
        echo(f"  status: {manifest.status}")

        manifest.loop_specific.stop_conditions.validate()
        echo("Stop conditions: PASS")

        if manifest.loop_specific.checker.rubric.dimensions:
            manifest.loop_specific.checker.rubric.validate_weights_sum()
            echo("Rubric weights: PASS")

    except Exception as exc:
        echo(f"Draft validation: FAIL -- {exc}", file=sys.stderr)
        if not force:
            echo("Fix validation errors before promoting, or use --force.", file=sys.stderr)
            return 1
        echo("[force] Proceeding despite validation failure.")

    # 2. Move draft files to official directory
    # First, ensure official dir exists
    official_dir.mkdir(parents=True, exist_ok=True)

    # Copy each file from draft to official
    for item in draft_dir.iterdir():
        if item.is_file():
            target = official_dir / item.name
            shutil.copy2(str(item), str(target))
            echo(f"  Promoted: {item.name}")

    # 3. Update status in loop.json from "draft" to "active"
    promoted_json = official_dir / "loop.json"
    if promoted_json.exists():
        data = json.loads(promoted_json.read_text(encoding="utf-8"))
        data["status"] = "active"
        promoted_json.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        echo("  Updated status: draft -> active")

    # 4. Remove draft directory
    shutil.rmtree(str(draft_dir))
    echo(f"  Removed draft directory: {draft_dir}")

    echo(f"\nPromoted loop '{loop_id}' to official.")
    echo(f"Location: {official_dir}")
    echo(f"\nNext steps:")
    echo(f"  loopctl validate {loop_id}")
    echo(f"  loopctl run {loop_id}")
    return 0
