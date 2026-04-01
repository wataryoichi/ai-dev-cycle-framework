"""Multi-cycle chain helpers — carry-forward, chain summary, stopped reasons."""

from __future__ import annotations

import json
from pathlib import Path

from .i18n import get_labels

# ── Stopped reason constants ─────────────────────────────────

STOPPED_BLOCKED = "blocked"
STOPPED_NEEDS_INPUT = "needs_input"
STOPPED_MAX_CYCLES = "max_cycles_reached"
STOPPED_STABLE = "stable"
STOPPED_COMPLETED = "completed"
STOPPED_NO_PROGRESS = "no_progress"
STOPPED_CLAUDE_TIMEOUT = "claude_timeout"
STOPPED_CODEX_TIMEOUT = "codex_timeout"
STOPPED_RUNNER_ERROR = "runner_error"
STOPPED_MAX_FIX_ROUNDS = "max_fix_rounds_reached"

ALL_STOPPED_REASONS = [
    STOPPED_BLOCKED, STOPPED_NEEDS_INPUT, STOPPED_MAX_CYCLES,
    STOPPED_STABLE, STOPPED_COMPLETED, STOPPED_NO_PROGRESS,
    STOPPED_CLAUDE_TIMEOUT, STOPPED_CODEX_TIMEOUT, STOPPED_RUNNER_ERROR,
    STOPPED_MAX_FIX_ROUNDS,
]


def build_carry_forward(previous_cycle_dir: Path) -> dict:
    """Build carry-forward context from previous cycle."""
    ctx = {"previous_cycle_dir": str(previous_cycle_dir)}

    # Load previous findings
    review_json = previous_cycle_dir / "review.json"
    if review_json.exists():
        try:
            review = json.loads(review_json.read_text())
            ctx["outstanding_findings"] = {
                "high": len(review.get("high", [])),
                "medium": len(review.get("medium", [])),
                "low": len(review.get("low", [])),
            }
        except Exception:
            pass

    # Load previous implementation summary
    impl_json = previous_cycle_dir / "implementation_summary.json"
    if impl_json.exists():
        try:
            impl = json.loads(impl_json.read_text())
            ctx["previous_summary"] = impl.get("summary", "")[:300]
        except Exception:
            pass

    # Load previous meta
    meta_path = previous_cycle_dir / "meta.json"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text())
            ctx["previous_cycle_id"] = meta.get("cycle_id", "")
            ctx["previous_version"] = meta.get("version", "")
            ctx["previous_state"] = meta.get("phase", "")
        except Exception:
            pass

    return ctx


def write_chain_summary(
    output_dir: Path,
    all_cycles: list[dict],
    stopped_reason: str,
    lang: str = "en",
) -> None:
    """Write chain-level summary as both JSON and Markdown."""
    L = get_labels(lang)

    data = {
        "requested_cycles": all_cycles[0].get("requested_cycles", len(all_cycles)) if all_cycles else 0,
        "executed_cycles": len(all_cycles),
        "stopped_reason": stopped_reason,
        "cycle_ids": [c.get("cycle_id", "") for c in all_cycles],
        "root_cycle_id": all_cycles[0].get("cycle_id", "") if all_cycles else "",
        "final_state": all_cycles[-1].get("state", "") if all_cycles else "",
        "final_tag": all_cycles[-1].get("tag", "") if all_cycles else "",
        "final_sha": all_cycles[-1].get("sha", "") if all_cycles else "",
        "lang": lang,
    }

    (output_dir / "run_summary.json").write_text(json.dumps(data, indent=2) + "\n")

    # Markdown
    if lang == "ja":
        md = "# 実行概要\n\n"
        md += f"- **実行サイクル数:** {data['executed_cycles']}\n"
        md += f"- **停止理由:** {stopped_reason}\n"
        md += f"- **最終状態:** {data['final_state']}\n\n"
        md += "## 各サイクル\n\n"
    else:
        md = "# Run Summary\n\n"
        md += f"- **Cycles executed:** {data['executed_cycles']}\n"
        md += f"- **Stopped:** {stopped_reason}\n"
        md += f"- **Final state:** {data['final_state']}\n\n"
        md += "## Cycles\n\n"

    for i, c in enumerate(all_cycles):
        md += f"### Cycle {i + 1}\n"
        md += f"- ID: `{c.get('cycle_id', '')}`\n"
        md += f"- State: {c.get('state', '')}\n"
        if c.get("tag"):
            md += f"- Tag: `{c['tag']}`\n"
        md += "\n"

    (output_dir / "run_summary.md").write_text(md)


def save_prompt_artifact(cycle_dir: Path, runner: str, prompt: str) -> None:
    """Save the prompt sent to a runner for debug/audit."""
    (cycle_dir / f"{runner}-prompt.txt").write_text(prompt)


def save_stderr_artifact(cycle_dir: Path, runner: str, stderr: str) -> None:
    """Save stderr from a runner for debugging."""
    if stderr and stderr.strip():
        (cycle_dir / f"{runner}-stderr.txt").write_text(stderr)


def build_fix_plan(cycle_dir: Path) -> dict:
    """Build a structured fix plan from review findings and followup."""
    plan = {"actions": [], "finding_count": 0}

    review_path = cycle_dir / "review.json"
    if review_path.exists():
        try:
            review = json.loads(review_path.read_text())
        except Exception:
            review = {}
    else:
        # Try codex-review.md parsing
        from .review_importer import parse_review
        cr = cycle_dir / "codex-review.md"
        review = parse_review(cr.read_text()) if cr.exists() else {}

    for severity in ("high", "medium", "low"):
        for finding in review.get(severity, []):
            if finding and finding != "(none)":
                plan["actions"].append({
                    "severity": severity,
                    "finding": finding,
                    "action_type": "fix",
                    "status": "pending",
                })
                plan["finding_count"] += 1

    # Save
    (cycle_dir / "fix_plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    return plan


def diff_findings(previous: dict, current: dict) -> dict:
    """Compare two review dicts and produce a diff."""
    prev_all = set()
    curr_all = set()
    for sev in ("high", "medium", "low"):
        for f in previous.get(sev, []):
            if f and f != "(none)":
                prev_all.add(f)
        for f in current.get(sev, []):
            if f and f != "(none)":
                curr_all.add(f)

    resolved = prev_all - curr_all
    new_findings = curr_all - prev_all
    unchanged = prev_all & curr_all

    result = {
        "resolved": list(resolved),
        "new": list(new_findings),
        "unchanged": list(unchanged),
        "previous_count": len(prev_all),
        "current_count": len(curr_all),
        "improved": len(curr_all) < len(prev_all),
        "no_progress": prev_all == curr_all,
    }
    return result


def build_fix_prompt(cycle_dir: Path, fix_plan: dict, spec: dict | None = None) -> str:
    """Build a prompt for Claude to fix the identified issues."""
    parts = ["Fix the following issues found during code review:\n"]

    for action in fix_plan.get("actions", []):
        parts.append(f"- [{action['severity'].upper()}] {action['finding']}")

    parts.append("\nRules:")
    parts.append("- Fix only the identified issues")
    parts.append("- Do not change unrelated code")
    parts.append("- Preserve existing passing behavior")

    if spec and spec.get("present"):
        if spec.get("constraints"):
            parts.append("\nSpec constraints to maintain:")
            for c in spec["constraints"][:5]:
                parts.append(f"  - {c}")
        if spec.get("acceptance_criteria"):
            parts.append("\nAcceptance criteria that must still pass:")
            for ac in spec["acceptance_criteria"][:5]:
                parts.append(f"  - {ac}")

    parts.append("\nAfter fixing, update claude-implementation-summary.md.")
    return "\n".join(parts)
