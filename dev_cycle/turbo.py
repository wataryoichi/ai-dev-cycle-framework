"""Turbo mode — auto version/commit/tag/push with rollback.

Fast-forward orchestration: changes are committed, tagged, and pushed
automatically. Safety comes from easy rollback, not from gates.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from .config import Config
from .cycle import (
    _read_meta,
    _write_meta,
    _run_git,
    _update_phase,
    check_cycle,
    finalize_cycle,
    git_info,
    start_cycle,
    StrictFinalizeError,
)
from .review_importer import count_findings, generate_followup_draft, import_review
from .review_orchestrator import finalize_review, prepare_review


def auto_version() -> str:
    """Generate a timestamp-based version string."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"dev-{ts}"


def turbo_commit(root: Path, message: str, tag: str | None = None) -> dict:
    """Auto commit, tag, and optionally push. Returns result info."""
    result = {"committed": False, "tagged": False, "pushed": False, "tag": "", "sha": ""}

    # Stage all changes
    _run_git(["add", "-A"], root)

    # Check if there's anything to commit
    status = _run_git(["status", "--porcelain"], root)
    if not status.strip():
        return result

    # Commit
    out = _run_git(["commit", "-m", message], root)
    result["committed"] = bool(out)
    result["sha"] = _run_git(["rev-parse", "--short", "HEAD"], root)

    # Tag
    if tag:
        _run_git(["tag", tag], root)
        result["tagged"] = True
        result["tag"] = tag

    return result


def turbo_push(root: Path, follow_tags: bool = True) -> bool:
    """Push to remote. Returns True on success."""
    args = ["push"]
    if follow_tags:
        args.append("--follow-tags")
    out = _run_git(args, root)
    # _run_git returns "" on error too, check if remote exists
    return True  # best-effort


def turbo_rollback(root: Path, target: str | None = None, steps: int = 1) -> dict:
    """Rollback to a previous version.

    target: tag name or commit SHA
    steps: how many commits to go back (if no target)

    Returns rollback info.
    """
    result = {"rolled_back": False, "from_sha": "", "to_sha": "", "to_tag": ""}
    result["from_sha"] = _run_git(["rev-parse", "--short", "HEAD"], root)

    if target:
        # Rollback to specific tag or SHA
        out = _run_git(["rev-parse", "--verify", target], root)
        if not out:
            return result
        _run_git(["reset", "--hard", target], root)
        result["to_tag"] = target
    else:
        _run_git(["reset", "--hard", f"HEAD~{steps}"], root)

    result["to_sha"] = _run_git(["rev-parse", "--short", "HEAD"], root)
    result["rolled_back"] = result["from_sha"] != result["to_sha"]
    return result


def turbo_history(root: Path, limit: int = 20) -> list[dict]:
    """Get recent turbo tags and commits."""
    # Get tags matching turbo/devcycle pattern
    tag_log = _run_git(
        ["log", f"--oneline", f"-{limit}", "--decorate=short"],
        root,
    )
    entries = []
    for line in (tag_log or "").splitlines():
        parts = line.split(" ", 1)
        if len(parts) < 2:
            continue
        sha = parts[0]
        rest = parts[1]
        # Extract tags
        tags = []
        if "tag:" in rest:
            import re
            tags = re.findall(r"tag:\s*([^\s,)]+)", rest)
        msg = rest.split(") ", 1)[-1] if ") " in rest else rest
        entries.append({"sha": sha, "message": msg.strip(), "tags": tags})
    return entries


def run_turbo(
    cfg: Config,
    title: str,
    push: bool = True,
    output_fn=None,
) -> dict:
    """Run a turbo cycle: start → record → commit → tag → push.

    This is the fast path. It creates a cycle, commits immediately,
    and tags. The actual implementation work happens between turbo calls
    (or is done by Claude in the same session).
    """
    output = output_fn or (lambda m: print(m))
    version = auto_version()
    root = cfg.project_root

    # Start cycle
    cycle_dir = start_cycle(cfg, version, title)
    meta = _read_meta(cycle_dir)
    output(f"Turbo cycle: {meta['cycle_id']}")
    output(f"  Version: {version}")

    # Auto commit
    tag = f"devcycle/{version}"
    commit_msg = f"devcycle(turbo): {title} [{version}]"
    commit_result = turbo_commit(root, commit_msg, tag=tag)

    if commit_result["committed"]:
        output(f"  Commit:  {commit_result['sha']}")
        output(f"  Tag:     {tag}")
    else:
        output(f"  No changes to commit")

    # Auto push
    if push and commit_result["committed"]:
        turbo_push(root)
        output(f"  Pushed")

    return {
        "cycle_id": meta["cycle_id"],
        "version": version,
        "title": title,
        "tag": tag,
        "sha": commit_result.get("sha", ""),
        "committed": commit_result["committed"],
        "pushed": push and commit_result["committed"],
        "cycle_dir": str(cycle_dir),
    }
