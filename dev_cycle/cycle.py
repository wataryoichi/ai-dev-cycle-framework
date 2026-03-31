"""Core cycle operations — create, finalize, query."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .config import Config

CYCLE_FILES = [
    "meta.json",
    "request.md",
    "claude-implementation-summary.md",
    "codex-review.md",
    "codex-followup.md",
    "final-summary.md",
    "self-application-notes.md",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _cycle_id(version: str, title: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    slug = title.lower().replace(" ", "-")[:40]
    return f"{version}_{ts}_{slug}"


def _run_git(args: list[str], cwd: Path) -> str:
    try:
        r = subprocess.run(
            ["git"] + args, capture_output=True, text=True, cwd=cwd, timeout=30
        )
        return r.stdout.strip()
    except Exception:
        return ""


def start_cycle(cfg: Config, version: str, title: str) -> Path:
    """Create a new cycle directory with initial files."""
    cid = _cycle_id(version, title)
    cycle_dir = cfg.cycle_root_path / cid
    cycle_dir.mkdir(parents=True, exist_ok=False)

    meta = {
        "cycle_id": cid,
        "version": version,
        "title": title,
        "status": "started",
        "started_at": _now_iso(),
        "finished_at": None,
        "project": cfg.project_name,
    }
    (cycle_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    (cycle_dir / "request.md").write_text(
        f"# Request — {title}\n\n"
        f"**Version:** {version}\n\n"
        "## Goal\n\n<!-- Describe the goal of this cycle -->\n\n"
        "## Notes\n\n<!-- Any constraints or context -->\n"
    )
    for name in [
        "claude-implementation-summary.md",
        "codex-review.md",
        "codex-followup.md",
        "final-summary.md",
        "self-application-notes.md",
    ]:
        (cycle_dir / name).write_text(f"# {name.replace('.md','').replace('-',' ').title()}\n\n<!-- To be filled -->\n")

    if cfg.store_git_status:
        status = _run_git(["status"], cfg.project_root)
        if status:
            (cycle_dir / "git-status.txt").write_text(status + "\n")

    if cfg.store_git_diff:
        diff = _run_git(["diff"], cfg.project_root)
        if diff:
            (cycle_dir / "git.diff").write_text(diff + "\n")

    return cycle_dir


def finalize_cycle(cfg: Config, cycle_dir: Path) -> None:
    """Mark a cycle as completed, update index and version history."""
    meta_path = cycle_dir / "meta.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"No meta.json in {cycle_dir}")

    meta = json.loads(meta_path.read_text())
    meta["status"] = "completed"
    meta["finished_at"] = _now_iso()
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")

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
        summary_text = "\n".join(l for l in lines if not l.startswith("# "))

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
