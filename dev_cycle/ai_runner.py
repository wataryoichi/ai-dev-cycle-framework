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


def run_claude(cycle_dir: Path, title: str, goal: str = "", spec: dict | None = None) -> dict:
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

    prompt = _build_impl_prompt(cycle_dir, title, goal, spec)

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


def run_codex(cycle_dir: Path, title: str, spec: dict | None = None) -> dict:
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

    prompt = _build_review_prompt(title, spec)

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


def _build_impl_prompt(cycle_dir: Path, title: str, goal: str,
                       spec: dict | None = None) -> str:
    """Build a structured prompt for Claude implementation."""
    request_path = cycle_dir / "request.md"
    request_content = request_path.read_text() if request_path.exists() else ""

    parts = [
        f"Implement the following:\n",
        f"Title: {title}",
        f"Goal: {goal or title}",
    ]

    if spec and spec.get("present"):
        parts.append(f"\nSpec: {spec.get('path', '')}")
        parts.append(f"Summary: {spec.get('summary', '')[:500]}")
        if spec.get("constraints"):
            parts.append(f"\nConstraints:")
            for c in spec["constraints"][:10]:
                parts.append(f"  - {c}")
        if spec.get("expected_outputs"):
            parts.append(f"\nExpected outputs:")
            for o in spec["expected_outputs"][:10]:
                parts.append(f"  - {o}")
        if spec.get("non_goals"):
            parts.append(f"\nNon-goals (do NOT implement):")
            for n in spec["non_goals"][:5]:
                parts.append(f"  - {n}")
        if spec.get("body"):
            parts.append(f"\nFull spec:\n{spec['body'][:2000]}")

    parts.extend([
        f"\nRequest:\n{request_content}",
        "\nAfter implementation, update claude-implementation-summary.md with:",
        "- What was done",
        "- Key decisions",
        "- Changed files",
        "- How to verify",
    ])
    return "\n".join(parts)


def _build_review_prompt(title: str, spec: dict | None = None) -> str:
    """Build a structured prompt for Codex review."""
    parts = [
        f"Review the changes for: {title}.",
        "Focus on correctness, edge cases, and maintainability.",
        "Structure findings as High / Medium / Low severity.",
    ]
    if spec and spec.get("present"):
        if spec.get("summary"):
            parts.append(f"Spec goal: {spec['summary'][:300]}")
        if spec.get("acceptance_criteria"):
            parts.append("Acceptance criteria:")
            for ac in spec["acceptance_criteria"][:5]:
                parts.append(f"  - {ac}")
        if spec.get("constraints"):
            parts.append("Constraints to verify:")
            for c in spec["constraints"][:5]:
                parts.append(f"  - {c}")
        if spec.get("non_goals"):
            parts.append("Non-goals (should NOT be implemented):")
            for n in spec["non_goals"][:3]:
                parts.append(f"  - {n}")
    return " ".join(parts)
