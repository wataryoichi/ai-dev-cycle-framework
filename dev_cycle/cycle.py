"""Core cycle operations — create, finalize, query."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from .config import Config


class StrictFinalizeError(Exception):
    """Raised when strict finalize is requested but quality checks fail."""
    def __init__(self, warnings: list[str]):
        self.warnings = warnings
        super().__init__(f"Strict finalize failed: {len(warnings)} issue(s)")


class NoCyclesError(Exception):
    """Raised when no cycle directories exist."""
    pass

# Ordered phases a cycle moves through.
# These names are canonical — used in CLI, docs, and commands.
PHASES = [
    "started",
    "implementation_done",
    "review_pending",
    "review_imported",
    "review_done",
    "followup_done",
    "completed",
]

# Phase → (what to do, suggested command, then command)
NEXT_STEPS: dict[str, tuple[str, str, str]] = {
    "started": (
        "Implement the changes, then update claude-implementation-summary.md",
        "devcycle prepare",
        "",
    ),
    "implementation_done": (
        "Prepare the cycle for Codex review",
        "devcycle prepare",
        "",
    ),
    "review_pending": (
        "Run Codex review and import the results",
        "devcycle review-loop --from-file codex-output.txt --generate-followup",
        "",
    ),
    "review_imported": (
        "Finalize the review phase",
        "devcycle finalize-review",
        "devcycle followup",
    ),
    "review_done": (
        "Generate follow-up draft, address findings, then finalize",
        "devcycle followup",
        "devcycle check",
    ),
    "followup_done": (
        "Check quality and finalize the cycle",
        "devcycle check",
        "devcycle finalize --strict",
    ),
    "completed": (
        "Cycle is complete. Start a new one when ready.",
        "devcycle start --version <V> --title <T>",
        "",
    ),
}

REVIEW_TEMPLATE = """\
# Codex Review

## Reviewer
Codex

## Summary
<!-- Overall review summary -->

## Findings

### High
<!-- Critical issues that must be fixed -->

### Medium
<!-- Important but not blocking -->

### Low
<!-- Minor suggestions or style issues -->

## Raw Notes
<!-- Optional: paste raw review output here -->
"""

FOLLOWUP_TEMPLATE = """\
# Codex Follow-up

## Accepted
<!-- - Finding: what was changed -->

## Deferred
<!-- - Finding: reason for deferral -->

## Rejected
<!-- - Finding: reason for rejection -->

## Additional Notes
<!-- Any extra context -->
"""

IMPLEMENTATION_SUMMARY_TEMPLATE = """\
# Claude Implementation Summary

## What Was Done
<!-- Describe the implementation -->

## Key Decisions
<!-- Any trade-offs or design choices -->

## Changed Files
<!-- List of files added/modified/deleted -->

## Testing
<!-- How was this verified? -->
"""

FINAL_SUMMARY_TEMPLATE = """\
# Final Summary

## Overview
<!-- One-paragraph summary of this cycle -->

## Changes
<!-- List of key changes -->

## Verification
<!-- How the changes were verified -->

## Remaining Issues
<!-- Any follow-up items -->
"""


def git_info(cwd: Path) -> dict:
    """Get git branch, HEAD SHA, and working tree status."""
    branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd) or ""
    sha = _run_git(["rev-parse", "--short", "HEAD"], cwd) or ""
    status_output = _run_git(["status", "--porcelain"], cwd)
    dirty = bool(status_output.strip()) if status_output else False
    detached = branch == "HEAD"
    return {
        "branch": branch if not detached else "(detached)",
        "head_sha": sha,
        "dirty": dirty,
        "detached": detached,
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _cycle_id(version: str, title: str) -> str:
    slug = title.lower().replace(" ", "-")[:40]
    # If version already contains a timestamp (turbo mode), skip adding another
    if version.startswith("dev-") and len(version) > 10:
        return f"{version}_{slug}"
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{version}_{ts}_{slug}"


def _run_git(args: list[str], cwd: Path) -> str:
    try:
        r = subprocess.run(
            ["git"] + args, capture_output=True, text=True, cwd=cwd, timeout=30
        )
        return r.stdout.strip()
    except Exception:
        return ""


def _read_meta(cycle_dir: Path) -> dict:
    meta_path = cycle_dir / "meta.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"No meta.json in {cycle_dir}")
    return json.loads(meta_path.read_text())


def _write_meta(cycle_dir: Path, meta: dict) -> None:
    (cycle_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")


def _update_phase(meta: dict, phase: str) -> dict:
    """Update phase, preserving backward compatibility."""
    meta["phase"] = phase
    if phase == "completed":
        meta["status"] = "completed"
    elif phase == "started":
        meta["status"] = "started"
    else:
        meta["status"] = "in_progress"
    return meta


# Lines that appear in templates but aren't real content
_TEMPLATE_LINES = frozenset({"Codex", "- (none)"})


def _is_placeholder(path: Path) -> bool:
    """Check if a file is still in its initial template state."""
    if not path.exists():
        return True
    content = path.read_text().strip()
    if not content:
        return True
    lines = [l for l in content.split("\n") if l.strip() and not l.strip().startswith("#")]
    return all(
        l.strip().startswith("<!--") or l.strip() in _TEMPLATE_LINES
        for l in lines
    )


def _resolve_cycle_dir(cfg: Config, cycle_dir_arg: str | None) -> Path:
    """Resolve a cycle dir from argument or fall back to latest.

    Raises NoCyclesError if no cycles exist and no dir was specified.
    """
    if cycle_dir_arg:
        p = Path(cycle_dir_arg)
        if not p.is_absolute():
            p = cfg.project_root / p
        return p
    latest = find_latest_cycle(cfg)
    if not latest:
        raise NoCyclesError("No cycles found. Start one with: start-cycle")
    return latest


def start_cycle(cfg: Config, version: str, title: str, spec: dict | None = None) -> Path:
    """Create a new cycle directory with initial files."""
    cid = _cycle_id(version, title)
    cycle_dir = cfg.cycle_root_path / cid
    cycle_dir.mkdir(parents=True, exist_ok=False)

    meta = {
        "cycle_id": cid,
        "version": version,
        "title": title,
        "status": "started",
        "phase": "started",
        "started_at": _now_iso(),
        "finished_at": None,
        "project": cfg.project_name,
    }
    if spec and spec.get("present"):
        meta["spec_path"] = spec.get("path", "")
        meta["spec_digest"] = spec.get("digest", "")
    _write_meta(cycle_dir, meta)

    # Dual output: Markdown + JSON for request
    from .dual_output import write_request
    goal = ""
    if spec and spec.get("present"):
        goal = spec.get("summary", "")[:200]
    write_request(cycle_dir, title, version, goal=goal,
                  context=f"Spec: {spec['path']}" if spec and spec.get("present") else "")

    # Spec fields in request.json
    if spec:
        req_json_path = cycle_dir / "request.json"
        if req_json_path.exists():
            req_data = json.loads(req_json_path.read_text())
            req_data["spec_path"] = spec.get("path", "")
            req_data["spec_present"] = spec.get("present", False)
            req_data["spec_digest"] = spec.get("digest", "")
            req_data["spec_summary"] = spec.get("summary", "")
            req_json_path.write_text(json.dumps(req_data, indent=2) + "\n")

    # Cycle state JSON
    state_data = {
        "cycle_id": cid, "state": "started", "version": version,
        "title": title, "started_at": meta["started_at"],
    }
    if spec and spec.get("present"):
        state_data["spec_path"] = spec.get("path", "")
        state_data["spec_digest"] = spec.get("digest", "")
    (cycle_dir / "cycle_state.json").write_text(json.dumps(state_data, indent=2) + "\n")

    # Markdown templates (backward compat)
    (cycle_dir / "claude-implementation-summary.md").write_text(IMPLEMENTATION_SUMMARY_TEMPLATE)
    (cycle_dir / "codex-review.md").write_text(REVIEW_TEMPLATE)
    (cycle_dir / "codex-followup.md").write_text(FOLLOWUP_TEMPLATE)
    (cycle_dir / "final-summary.md").write_text(FINAL_SUMMARY_TEMPLATE)
    (cycle_dir / "self-application-notes.md").write_text(
        "# Self-Application Notes\n\n"
        "## Change Type\n\n"
        "<!-- user-facing feature / internal tooling / documentation -->\n\n"
        "## Impact on Framework Development\n\n"
        "<!-- How does this improve the framework's own dev workflow? -->\n"
    )

    if cfg.store_git_status:
        status = _run_git(["status"], cfg.project_root)
        if status:
            (cycle_dir / "git-status.txt").write_text(status + "\n")

    if cfg.store_git_diff:
        diff = _run_git(["diff"], cfg.project_root)
        if diff:
            (cycle_dir / "git.diff").write_text(diff + "\n")

    return cycle_dir


def check_cycle(cycle_dir: Path) -> dict:
    """Check cycle quality. Returns dict with ready/issues/phase."""
    meta = _read_meta(cycle_dir)
    phase = meta.get("phase", meta.get("status", "started"))

    files = {
        "request.md": "Request",
        "claude-implementation-summary.md": "Implementation summary",
        "codex-review.md": "Codex review",
        "codex-followup.md": "Codex follow-up",
        "final-summary.md": "Final summary",
    }

    ready = []
    placeholder = []
    missing = []

    for filename, label in files.items():
        path = cycle_dir / filename
        if not path.exists():
            missing.append(f"{filename}: {label} — missing")
        elif _is_placeholder(path):
            placeholder.append(f"{filename}: {label} — still template")
        else:
            ready.append(f"{filename}: {label}")

    # Section checks on final-summary
    section_warnings = []
    fs = cycle_dir / "final-summary.md"
    if fs.exists() and not _is_placeholder(fs):
        content = fs.read_text()
        for section in ["## Overview", "## Changes"]:
            if section not in content:
                section_warnings.append(f"final-summary.md: missing {section}")

    all_issues = missing + placeholder + section_warnings
    can_finalize = not any(
        f.startswith("claude-implementation-summary.md") or f.startswith("final-summary.md")
        for f in missing + placeholder
    )

    return {
        "phase": phase,
        "ready": ready,
        "placeholder": placeholder,
        "missing": missing,
        "section_warnings": section_warnings,
        "all_issues": all_issues,
        "can_finalize": can_finalize and not section_warnings,
    }


def finalize_cycle(cfg: Config, cycle_dir: Path, strict: bool = False) -> list[str]:
    """Mark a cycle as completed, update index and version history.

    Returns a list of warnings (empty if all looks good).
    """
    meta = _read_meta(cycle_dir)
    result = check_cycle(cycle_dir)
    warnings = result["all_issues"]

    if strict and warnings:
        raise StrictFinalizeError(warnings)

    _update_phase(meta, "completed")
    meta["finished_at"] = _now_iso()
    _write_meta(cycle_dir, meta)

    if cfg.store_git_status:
        status = _run_git(["status"], cfg.project_root)
        if status:
            (cycle_dir / "git-status.txt").write_text(status + "\n")
    if cfg.store_git_diff:
        diff = _run_git(["diff"], cfg.project_root)
        if diff:
            (cycle_dir / "git.diff").write_text(diff + "\n")

    _append_index(cfg, meta)
    _append_version_history(cfg, meta, cycle_dir)

    return warnings


def next_step(cycle_dir: Path) -> dict:
    """Determine the next action based on current phase + quality."""
    from .review_importer import count_findings

    meta = _read_meta(cycle_dir)
    phase = meta.get("phase", meta.get("status", "started"))
    action, command, then = NEXT_STEPS.get(phase, ("Unknown phase", "", ""))
    quality = check_cycle(cycle_dir)
    findings = count_findings(cycle_dir)
    strict_ready = not quality["all_issues"]
    rereview = _detect_rereview_hint(cycle_dir)

    return {
        "cycle_id": meta["cycle_id"],
        "version": meta["version"],
        "title": meta["title"],
        "phase": phase,
        "action": action,
        "command": command,
        "then": then,
        "cycle_dir": str(cycle_dir),
        "ready_count": len(quality["ready"]),
        "placeholder_count": len(quality["placeholder"]),
        "missing_count": len(quality["missing"]),
        "findings_high": findings["high"],
        "findings_medium": findings["medium"],
        "findings_low": findings["low"],
        "findings_total": findings["total"],
        "can_finalize": quality["can_finalize"],
        "strict_ready": strict_ready,
        "rereview_hint": rereview,
    }


def _detect_rereview_hint(cycle_dir: Path) -> str:
    """Heuristic: suggest re-review if HIGH findings were accepted."""
    followup = cycle_dir / "codex-followup.md"
    if not followup.exists() or _is_placeholder(followup):
        return "unknown"
    content = followup.read_text()
    accepted_match = re.search(r"## Accepted\s*\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
    if accepted_match:
        accepted = accepted_match.group(1)
        if "[HIGH]" in accepted:
            return "recommended"
        if "[MEDIUM]" in accepted:
            return "optional"
    return "not_needed"


def _append_index(cfg: Config, meta: dict) -> None:
    index_path = cfg.cycle_root_path / "index.jsonl"
    with open(index_path, "a") as f:
        f.write(json.dumps(meta) + "\n")


def _append_version_history(cfg: Config, meta: dict, cycle_dir: Path) -> None:
    history_path = cfg.version_history_path
    history_path.parent.mkdir(parents=True, exist_ok=True)

    summary_text = ""
    final_summary = cycle_dir / "final-summary.md"
    if final_summary.exists():
        content = final_summary.read_text().strip()
        lines = content.split("\n")
        summary_text = "\n".join(
            l for l in lines
            if not l.strip().startswith("#") and not l.strip().startswith("<!--")
        )

    entry = (
        f"\n### {meta['version']} — {meta['title']}\n\n"
        f"- **Cycle:** `{meta['cycle_id']}`\n"
        f"- **Started:** {meta.get('started_at', 'N/A')}\n"
        f"- **Completed:** {meta.get('finished_at', 'N/A')}\n"
    )
    if summary_text.strip():
        entry += f"\n{summary_text.strip()}\n"

    if not history_path.exists():
        history_path.write_text("# Version History\n")

    with open(history_path, "a") as f:
        f.write(entry)


def load_index(cfg: Config) -> list[dict]:
    index_path = cfg.cycle_root_path / "index.jsonl"
    if not index_path.exists():
        return []
    entries = []
    for line in index_path.read_text().splitlines():
        line = line.strip()
        if line:
            entries.append(json.loads(line))
    return entries


def find_latest_cycle(cfg: Config) -> Path | None:
    """Find the most recently created cycle directory."""
    root = cfg.cycle_root_path
    if not root.exists():
        return None
    dirs = sorted(
        [d for d in root.iterdir() if d.is_dir() and (d / "meta.json").exists()],
        key=lambda d: d.name,
        reverse=True,
    )
    return dirs[0] if dirs else None


def get_cycle_phase(cycle_dir: Path) -> str:
    """Get the current phase of a cycle, with backward compat."""
    meta = _read_meta(cycle_dir)
    if "phase" in meta:
        return meta["phase"]
    return meta.get("status", "started")
