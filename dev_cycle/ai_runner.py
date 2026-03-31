"""AI runner — execute Claude implementation and Codex review as subprocesses.

Runners are invoked by the orchestrator when a cycle reaches the
implementing or review_needed state. If the command is not configured,
the runner returns a block result instead of failing.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


def get_claude_cmd() -> str:
    """Get Claude command from env."""
    return os.environ.get("DEVCYCLE_CLAUDE_CMD", "")


def get_codex_cmd() -> str:
    """Get Codex command from env."""
    return os.environ.get("DEVCYCLE_CODEX_CMD", "")


def run_claude(cycle_dir: Path, title: str, goal: str = "") -> dict:
    """Run Claude implementation. Returns result dict.

    If DEVCYCLE_CLAUDE_CMD is not set, returns blocked result.
    The command receives a structured prompt via stdin.
    """
    cmd = get_claude_cmd()
    if not cmd:
        return {
            "success": False,
            "blocked": True,
            "reason": "DEVCYCLE_CLAUDE_CMD not set",
            "output": "",
        }

    prompt = _build_impl_prompt(cycle_dir, title, goal)

    try:
        result = subprocess.run(
            cmd, shell=True, input=prompt, capture_output=True,
            text=True, timeout=300, cwd=cycle_dir.parent.parent,
        )
        return {
            "success": result.returncode == 0,
            "blocked": False,
            "reason": "" if result.returncode == 0 else f"exit code {result.returncode}",
            "output": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "blocked": False, "reason": "timeout", "output": ""}
    except Exception as e:
        return {"success": False, "blocked": False, "reason": str(e), "output": ""}


def run_codex(cycle_dir: Path, title: str) -> dict:
    """Run Codex review. Returns result dict with review text.

    If DEVCYCLE_CODEX_CMD is not set, returns blocked result.
    The command receives a review prompt as its argument.
    """
    cmd = get_codex_cmd()
    if not cmd:
        return {
            "success": False,
            "blocked": True,
            "reason": "DEVCYCLE_CODEX_CMD not set",
            "review_text": "",
        }

    prompt = _build_review_prompt(title)

    try:
        result = subprocess.run(
            f'{cmd} "{prompt}"', shell=True, capture_output=True,
            text=True, timeout=300, cwd=cycle_dir.parent.parent,
        )
        review_text = result.stdout.strip()
        return {
            "success": result.returncode == 0 and bool(review_text),
            "blocked": False,
            "reason": "" if review_text else "empty review output",
            "review_text": review_text,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "blocked": False, "reason": "timeout", "review_text": ""}
    except Exception as e:
        return {"success": False, "blocked": False, "reason": str(e), "review_text": ""}


def _build_impl_prompt(cycle_dir: Path, title: str, goal: str) -> str:
    """Build a structured prompt for Claude implementation."""
    request_path = cycle_dir / "request.md"
    request_content = request_path.read_text() if request_path.exists() else ""

    return (
        f"Implement the following:\n\n"
        f"Title: {title}\n"
        f"Goal: {goal or title}\n\n"
        f"Request:\n{request_content}\n\n"
        f"After implementation, update claude-implementation-summary.md with:\n"
        f"- What was done\n"
        f"- Key decisions\n"
        f"- Changed files\n"
        f"- How to verify\n"
    )


def _build_review_prompt(title: str) -> str:
    """Build a structured prompt for Codex review."""
    return (
        f"Review the changes for: {title}. "
        f"Focus on correctness, edge cases, and maintainability. "
        f"Structure findings as High / Medium / Low severity."
    )
