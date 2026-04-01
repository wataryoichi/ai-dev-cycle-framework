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
    spec_path: str | None = None,
    lang: str = "en",
    cycles: int = 1,
    max_fix_rounds: int = 3,
    input_fn=None,
    output_fn=None,
) -> dict:
    """Run turbo cycle(s): orchestrate → commit → tag → push.

    Supports multi-cycle via `cycles` parameter.
    """
    output = output_fn or (lambda m: print(m))
    root = cfg.project_root

    from .spec_reader import find_spec, read_spec, empty_spec
    spec_file = find_spec(root, spec_path)
    spec = read_spec(spec_file) if spec_file else empty_spec()

    from .chain import (
        build_carry_forward, write_chain_summary,
        STOPPED_BLOCKED, STOPPED_MAX_CYCLES, STOPPED_COMPLETED,
    )

    all_cycles = []
    prev_cycle_id = ""
    prev_cycle_dir = None
    root_cycle_id = ""
    stopped_reason = STOPPED_MAX_CYCLES

    for iteration in range(cycles):
        import time
        if iteration > 0:
            time.sleep(1)  # ensure unique timestamp

        version = auto_version()
        tag = f"devcycle/{version}"

        if cycles > 1:
            output(f"\n── Cycle {iteration + 1}/{cycles} ──")

        if spec["present"]:
            output(f"  Spec: {spec['path']}")

        cycle_dir = start_cycle(cfg, version, title, spec=spec, lang=lang)
        meta = _read_meta(cycle_dir)

        if iteration == 0:
            root_cycle_id = meta["cycle_id"]

        # Record multi-cycle context + carry-forward
        meta["root_cycle_id"] = root_cycle_id
        meta["iteration_index"] = iteration
        meta["iteration_total"] = cycles
        if prev_cycle_id:
            meta["previous_cycle_id"] = prev_cycle_id
        if prev_cycle_dir:
            carry = build_carry_forward(prev_cycle_dir)
            meta["carry_forward"] = carry
        _write_meta(cycle_dir, meta)

        output(f"Turbo: {meta['cycle_id']}")
        output(f"  Version: {version}")

        if dry_run:
            output(f"  [dry-run] Would orchestrate, then commit as {tag}")
            all_cycles.append({
                "cycle_id": meta["cycle_id"], "version": version, "state": "started",
                "tag": tag, "dry_run": True,
            })
            break

        orch_result = _drive(cfg, cycle_dir, input_fn, output, non_interactive, max_fix_rounds)
        state = orch_result.state

        # Generate README at project root
        from .orchestrator import _generate_readme
        readme_path = _generate_readme(cycle_dir, root)
        if readme_path:
            output(f"  → README.md generated")

        # Git afterburner
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

        cycle_info = {
            "cycle_id": meta["cycle_id"], "version": version, "title": title,
            "tag": tag if commit_result["tagged"] else "",
            "sha": commit_result.get("sha", ""),
            "committed": commit_result["committed"],
            "pushed": commit_result.get("pushed", False),
            "state": state.value,
            "interrupted": orch_result.interrupted,
            "blocked": orch_result.blocked,
            "blocked_reason": orch_result.blocked_reason,
            "cycle_dir": str(cycle_dir),
        }
        all_cycles.append(cycle_info)
        prev_cycle_id = meta["cycle_id"]
        prev_cycle_dir = cycle_dir

        # Stop conditions
        if orch_result.blocked or orch_result.interrupted:
            stopped_reason = STOPPED_BLOCKED
            break
        if state == State.COMPLETED:
            stopped_reason = STOPPED_COMPLETED
            continue

    # Write chain summary if multi-cycle
    if cycles > 1:
        write_chain_summary(cfg.cycle_root_path, all_cycles, stopped_reason, lang=lang)

    # Return last cycle result + multi-cycle summary
    last = all_cycles[-1] if all_cycles else {}
    last["requested_cycles"] = cycles
    last["executed_cycles"] = len(all_cycles)
    last["stopped_reason"] = stopped_reason
    last["root_cycle_id"] = root_cycle_id
    last["all_cycles"] = [c["cycle_id"] for c in all_cycles]
    last["history"] = getattr(orch_result, "history", []) if 'orch_result' in dir() else []
    return last
