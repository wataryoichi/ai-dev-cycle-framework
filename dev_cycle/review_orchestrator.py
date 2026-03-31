"""Review orchestration — prepare and finalize review phases."""

from __future__ import annotations

import sys
from pathlib import Path

from .config import Config
from .cycle import (
    FOLLOWUP_TEMPLATE,
    REVIEW_TEMPLATE,
    _is_placeholder,
    _read_meta,
    _run_git,
    _update_phase,
    _write_meta,
)


def prepare_review(cfg: Config, cycle_dir: Path) -> dict:
    """Prepare a cycle for Codex review.

    Returns a summary dict with cycle info and next-step guidance.
    """
    meta = _read_meta(cycle_dir)

    # Ensure review template is ready
    review_path = cycle_dir / "codex-review.md"
    if _is_placeholder(review_path):
        review_path.write_text(REVIEW_TEMPLATE)

    # Update phase
    _update_phase(meta, "review_pending")
    _write_meta(cycle_dir, meta)

    # Gather context for review
    branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cfg.project_root) or "unknown"
    recent_commits = _run_git(
        ["log", "--oneline", "-10"], cfg.project_root
    )

    return {
        "cycle_id": meta["cycle_id"],
        "version": meta["version"],
        "title": meta["title"],
        "phase": meta["phase"],
        "branch": branch,
        "cycle_dir": str(cycle_dir),
        "review_file": str(review_path),
        "recent_commits": recent_commits,
    }


def finalize_review(cfg: Config, cycle_dir: Path) -> list[str]:
    """Mark review as done and prepare for follow-up phase.

    Returns a list of warnings.
    """
    meta = _read_meta(cycle_dir)
    warnings = []

    review_path = cycle_dir / "codex-review.md"
    followup_path = cycle_dir / "codex-followup.md"

    if _is_placeholder(review_path):
        warnings.append(
            "codex-review.md is still empty. "
            "Run Codex review and paste results before finalizing."
        )

    # Ensure followup template is ready for the next phase
    if _is_placeholder(followup_path):
        followup_path.write_text(FOLLOWUP_TEMPLATE)

    _update_phase(meta, "review_done")
    _write_meta(cycle_dir, meta)

    return warnings
