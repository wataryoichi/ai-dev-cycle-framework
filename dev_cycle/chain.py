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

ALL_STOPPED_REASONS = [
    STOPPED_BLOCKED, STOPPED_NEEDS_INPUT, STOPPED_MAX_CYCLES,
    STOPPED_STABLE, STOPPED_COMPLETED, STOPPED_NO_PROGRESS,
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
