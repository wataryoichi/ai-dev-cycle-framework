"""Turbo mode — aggressive orchestration + auto version/commit/tag/push.

Turbo integrates the full state machine (Claude→Codex→Claude) with
automatic git operations at the end. The dev cycle is the main event;
git automation is the afterburner.
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
from .orchestrator import RunResult, _drive
from .review_importer import count_findings
from .state_machine import Choice, State, determine_state


def auto_version() -> str:
    """Generate a timestamp-based version string."""
    return f"dev-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"


def turbo_commit(root: Path, message: str, tag: str | None = None) -> dict:
    """Commit all changes, optionally tag."""
    result = {"committed": False, "tagged": False, "pushed": False, "tag": "", "sha": ""}
    _run_git(["add", "-A"], root)
    status = _run_git(["status", "--porcelain"], root)
    if not status.strip():
        return result
    _run_git(["commit", "-m", message], root)
    result["committed"] = True
    result["sha"] = _run_git(["rev-parse", "--short", "HEAD"], root)
    if tag:
        _run_git(["tag", tag], root)
        result["tagged"] = True
        result["tag"] = tag
    return result


def turbo_push(root: Path) -> bool:
    _run_git(["push", "--follow-tags"], root)
    return True


def turbo_rollback(root: Path, target: str | None = None, steps: int = 1,
                   reason: str = "") -> dict:
    """Rollback and record the action."""
    result = {
        "rolled_back": False, "from_sha": "", "to_sha": "", "to_tag": "",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "reason": reason,
    }
    result["from_sha"] = _run_git(["rev-parse", "--short", "HEAD"], root)
    if target:
        out = _run_git(["rev-parse", "--verify", target], root)
        if not out:
            return result
        _run_git(["reset", "--hard", target], root)
        result["to_tag"] = target
    else:
        _run_git(["reset", "--hard", f"HEAD~{steps}"], root)
    result["to_sha"] = _run_git(["rev-parse", "--short", "HEAD"], root)
    result["rolled_back"] = result["from_sha"] != result["to_sha"]

    # Record rollback
    if result["rolled_back"]:
        _record_rollback(root, result)

    return result


def _record_rollback(root: Path, info: dict) -> None:
    """Save rollback record as Markdown + JSON."""
    rollback_dir = root / "ops" / "rollbacks"
    rollback_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    base = f"rollback-{ts}"

    # JSON
    (rollback_dir / f"{base}.json").write_text(json.dumps(info, indent=2) + "\n")

    # Markdown
    md = (
        f"# Rollback — {ts}\n\n"
        f"- **From:** `{info['from_sha']}`\n"
        f"- **To:** `{info['to_sha']}`\n"
    )
    if info.get("to_tag"):
        md += f"- **Tag:** `{info['to_tag']}`\n"
    if info.get("reason"):
        md += f"- **Reason:** {info['reason']}\n"
    md += f"- **Time:** {info['timestamp']}\n"

    (rollback_dir / f"{base}.md").write_text(md)


def turbo_history(root: Path, limit: int = 20) -> list[dict]:
    import re
    tag_log = _run_git(["log", f"--oneline", f"-{limit}", "--decorate=short"], root)
    entries = []
    for line in (tag_log or "").splitlines():
        parts = line.split(" ", 1)
        if len(parts) < 2:
            continue
        sha = parts[0]
        rest = parts[1]
        tags = re.findall(r"tag:\s*([^\s,)]+)", rest) if "tag:" in rest else []
        msg = rest.split(") ", 1)[-1] if ") " in rest else rest
        entries.append({"sha": sha, "message": msg.strip(), "tags": tags})
    return entries


def run_turbo(
    cfg: Config,
    title: str,
    push: bool = True,
    non_interactive: bool = False,
    dry_run: bool = False,
    input_fn=None,
    output_fn=None,
) -> dict:
    """Run a turbo cycle: orchestrate → commit → tag → push.

    The orchestrator drives Claude→Codex→Claude.
    Git operations happen only after the cycle completes or reaches a stable state.
    """
    output = output_fn or (lambda m: print(m))
    version = auto_version()
    root = cfg.project_root
    tag = f"devcycle/{version}"

    # Phase 1: Orchestrate the dev cycle
    cycle_dir = start_cycle(cfg, version, title)
    meta = _read_meta(cycle_dir)
    output(f"Turbo: {meta['cycle_id']}")
    output(f"  Version: {version}")

    if dry_run:
        output(f"  [dry-run] Would orchestrate cycle, then commit as {tag}")
        return {
            "cycle_id": meta["cycle_id"], "version": version, "title": title,
            "tag": tag, "sha": "", "committed": False, "pushed": False,
            "state": "started", "dry_run": True, "cycle_dir": str(cycle_dir),
        }

    # Run the orchestrator (same engine as `devcycle run`)
    orch_result = _drive(cfg, cycle_dir, input_fn, output, non_interactive)

    # Phase 2: Git operations (afterburner)
    state = orch_result.state
    commit_result = {"committed": False, "tagged": False, "sha": "", "tag": ""}

    commit_msg = f"devcycle(turbo): {title} [{version}] state:{state.value}"
    commit_result = turbo_commit(root, commit_msg, tag=tag)
    if commit_result["committed"]:
        output(f"  Commit: {commit_result['sha']}")
        output(f"  Tag:    {tag}")

    if push and commit_result["committed"]:
        turbo_push(root)
        output(f"  Pushed")
        commit_result["pushed"] = True

    return {
        "cycle_id": meta["cycle_id"],
        "version": version,
        "title": title,
        "tag": tag if commit_result["tagged"] else "",
        "sha": commit_result.get("sha", ""),
        "committed": commit_result["committed"],
        "pushed": commit_result.get("pushed", False),
        "state": state.value,
        "interrupted": orch_result.interrupted,
        "blocked": orch_result.blocked,
        "blocked_reason": orch_result.blocked_reason,
        "cycle_dir": str(cycle_dir),
        "history": orch_result.history,
    }
