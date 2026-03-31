"""Environment diagnostics for devcycle."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from . import __version__
from .config import DEFAULT_CONFIG_NAME


def run_doctor(project_root: Path) -> dict:
    """Run all diagnostic checks. Returns structured result."""
    root = project_root.resolve()
    checks = []

    # 1. Python version
    pyver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    checks.append(_check("python_version", f"Python {pyver}", "ok"))

    # 2. Package version
    checks.append(_check("devcycle_version", f"devcycle {__version__}", "ok"))

    # 3. Config file
    config_path = root / DEFAULT_CONFIG_NAME
    if config_path.exists():
        checks.append(_check("config", f"Config found: {DEFAULT_CONFIG_NAME}", "ok"))
    else:
        checks.append(_check("config", f"Config not found: {DEFAULT_CONFIG_NAME}", "error",
                              fix="Create devcycle.config.json in project root"))

    # 4. Cycle root
    cycle_root = root / "ops" / "dev-cycles"
    if config_path.exists():
        import json
        try:
            data = json.loads(config_path.read_text())
            cycle_root = root / data.get("cycle_root", "ops/dev-cycles")
        except Exception:
            pass
    if cycle_root.exists():
        checks.append(_check("cycle_root", f"Cycle root exists: {cycle_root.relative_to(root)}", "ok"))
    else:
        checks.append(_check("cycle_root", f"Cycle root missing: {cycle_root.relative_to(root)}", "error",
                              fix=f"mkdir -p {cycle_root.relative_to(root)}"))

    # 5. Git repository
    git_dir = root / ".git"
    if git_dir.exists():
        checks.append(_check("git", "Git repository detected", "ok"))
    else:
        checks.append(_check("git", "Not a git repository", "warn"))

    # 6. Hooks
    hooks_dir = root / "scripts" / "hooks"
    post_commit = hooks_dir / "post-commit"
    if post_commit.exists():
        checks.append(_check("hook_autotag", "Auto-tag hook installed", "ok"))
    elif hooks_dir.exists():
        checks.append(_check("hook_autotag", "Auto-tag hook not installed", "warn",
                              fix="devcycle setup-hooks"))
    else:
        checks.append(_check("hook_autotag", "scripts/hooks/ directory missing", "warn"))

    # 7. Review hook
    review_hook = hooks_dir / "post-prepare-review"
    review_sample = hooks_dir / "post-prepare-review.sample"
    if review_hook.exists():
        checks.append(_check("hook_review", "Review hook installed", "ok"))
    elif review_sample.exists():
        checks.append(_check("hook_review", "Review hook not installed (sample available)", "warn",
                              fix=f"cp {review_sample.relative_to(root)} {review_hook.relative_to(root)}"))
    else:
        checks.append(_check("hook_review", "Review hook sample not found", "warn"))

    # 8. DEVCYCLE_CODEX_CMD
    codex_cmd = os.environ.get("DEVCYCLE_CODEX_CMD", "")
    if codex_cmd:
        checks.append(_check("codex_cmd", f"DEVCYCLE_CODEX_CMD set: {codex_cmd}", "ok"))
    else:
        checks.append(_check("codex_cmd", "DEVCYCLE_CODEX_CMD not set", "warn",
                              fix="export DEVCYCLE_CODEX_CMD='codex review --prompt'"))

    # 9. Write access
    try:
        test_file = root / ".devcycle_write_test"
        test_file.write_text("test")
        test_file.unlink()
        checks.append(_check("write_access", "Write access confirmed", "ok"))
    except Exception:
        checks.append(_check("write_access", "No write access to project root", "error"))

    # 10. Latest cycle
    try:
        from .config import Config
        from .cycle import find_latest_cycle
        if config_path.exists():
            cfg = Config.load(root)
            latest = find_latest_cycle(cfg)
            if latest:
                checks.append(_check("latest_cycle", f"Latest cycle: {latest.name}", "ok"))
            else:
                checks.append(_check("latest_cycle", "No cycles found", "warn",
                                      fix="devcycle start --version v0.1.0 --title 'first cycle'"))
    except Exception:
        checks.append(_check("latest_cycle", "Could not check cycles", "warn"))

    # Summary
    statuses = [c["status"] for c in checks]
    if "error" in statuses:
        overall = "error"
    elif "warn" in statuses:
        overall = "warn"
    else:
        overall = "ok"

    return {
        "status": overall,
        "checks": checks,
        "version": __version__,
        "python_version": pyver,
        "project_root": str(root),
    }


def _check(name: str, message: str, status: str, fix: str = "") -> dict:
    result = {"name": name, "message": message, "status": status}
    if fix:
        result["fix"] = fix
    return result


def format_doctor(result: dict) -> str:
    """Format doctor result for human display."""
    lines = []
    status_icons = {"ok": "OK   ", "warn": "WARN ", "error": "ERROR"}

    for check in result["checks"]:
        icon = status_icons.get(check["status"], "?    ")
        lines.append(f"[{icon}] {check['message']}")

    lines.append("")
    overall = result["status"].upper()
    lines.append(f"Doctor result: {overall}")

    # Collect suggested fixes
    fixes = [c["fix"] for c in result["checks"] if c.get("fix")]
    if fixes:
        lines.append("")
        lines.append("Suggested actions:")
        for fix in fixes:
            lines.append(f"  $ {fix}")

    return "\n".join(lines)
