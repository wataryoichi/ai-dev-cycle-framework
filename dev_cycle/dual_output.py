"""Dual output — write both Markdown and JSON for cycle records.

Each record type has a structured dict as source of truth.
render_md() and serialize_json() produce the two output formats.
"""

from __future__ import annotations

import json
from pathlib import Path


def write_dual(cycle_dir: Path, name: str, data: dict, md_content: str) -> None:
    """Write both <name>.json and <name>.md to cycle_dir."""
    (cycle_dir / f"{name}.json").write_text(json.dumps(data, indent=2) + "\n")
    (cycle_dir / f"{name}.md").write_text(md_content)


def write_request(cycle_dir: Path, title: str, version: str,
                  goal: str = "", context: str = "", scope: str = "", notes: str = "",
                  spec: dict | None = None) -> None:
    data = {"title": title, "version": version, "goal": goal,
            "context": context, "scope": scope, "notes": notes}
    if spec and spec.get("present"):
        data["spec_path"] = spec.get("path", "")
        data["spec_present"] = True
        data["spec_digest"] = spec.get("digest", "")
        data["spec_summary"] = spec.get("summary", "")
        data["spec_constraints"] = spec.get("constraints", [])
        data["spec_expected_outputs"] = spec.get("expected_outputs", [])

    md = (
        f"# Request — {title}\n\n"
        f"**Version:** {version}\n\n"
        f"## Goal\n\n{goal or '<!-- Describe the goal -->'}\n\n"
        f"## Context\n\n{context or '<!-- Why is this needed? -->'}\n\n"
        f"## Scope\n\n{scope or '<!-- In scope / out of scope -->'}\n\n"
        f"## Notes\n\n{notes or '<!-- Constraints, dependencies -->'}\n"
    )

    if spec and spec.get("present"):
        md += f"\n## Spec\n\n"
        md += f"- **Path:** `{spec.get('path', '')}`\n"
        md += f"- **Digest:** `{spec.get('digest', '')}`\n"
        if spec.get("summary"):
            md += f"\n{spec['summary'][:300]}\n"
        if spec.get("constraints"):
            md += f"\n### Constraints\n"
            for c in spec["constraints"][:10]:
                md += f"- {c}\n"
        if spec.get("expected_outputs"):
            md += f"\n### Expected Outputs\n"
            for o in spec["expected_outputs"][:10]:
                md += f"- {o}\n"

    write_dual(cycle_dir, "request", data, md)


def write_review(cycle_dir: Path, summary: str = "", high: list[str] | None = None,
                 medium: list[str] | None = None, low: list[str] | None = None,
                 raw: str = "") -> None:
    data = {"summary": summary, "high": high or [], "medium": medium or [],
            "low": low or [], "raw": raw}
    # Also write as codex-review.md for backward compat
    from .review_importer import format_review
    md = format_review(data)
    write_dual(cycle_dir, "review", data, md)
    # Backward compat
    (cycle_dir / "codex-review.md").write_text(md)


def write_followup(cycle_dir: Path, accepted: list[dict] | None = None,
                   deferred: list[dict] | None = None,
                   rejected: list[dict] | None = None, notes: str = "") -> None:
    data = {"accepted": accepted or [], "deferred": deferred or [],
            "rejected": rejected or [], "notes": notes}
    lines = ["# Codex Follow-up\n\n## Accepted"]
    for item in (accepted or []):
        lines.append(f"- [{item.get('severity', '?')}] {item.get('finding', '')}: {item.get('action', '<!-- action -->')}")
    lines.extend(["\n## Deferred"])
    for item in (deferred or []):
        lines.append(f"- {item.get('finding', '')}: {item.get('reason', '')}")
    lines.extend(["\n## Rejected"])
    for item in (rejected or []):
        lines.append(f"- {item.get('finding', '')}: {item.get('reason', '')}")
    if notes:
        lines.extend([f"\n## Notes\n{notes}"])
    lines.append("")
    md = "\n".join(lines)
    write_dual(cycle_dir, "followup", data, md)
    (cycle_dir / "codex-followup.md").write_text(md)


def write_final_summary(cycle_dir: Path, overview: str = "", changes: list[str] | None = None,
                        verification: str = "", remaining: list[str] | None = None) -> None:
    data = {"overview": overview, "changes": changes or [],
            "verification": verification, "remaining": remaining or []}
    md = (
        f"# Final Summary\n\n"
        f"## Overview\n{overview or '<!-- summary -->'}\n\n"
        f"## Changes\n"
    )
    for c in (changes or []):
        md += f"- {c}\n"
    md += f"\n## Verification\n{verification or '<!-- how verified -->'}\n\n"
    md += f"## Remaining Issues\n"
    for r in (remaining or []):
        md += f"- {r}\n"
    write_dual(cycle_dir, "final_summary", data, md)
    (cycle_dir / "final-summary.md").write_text(md)


def write_implementation_summary(
    cycle_dir: Path, title: str = "", summary: str = "",
    key_decisions: list[str] | None = None,
    files_changed: list[str] | None = None,
    verification: str = "",
    known_limitations: list[str] | None = None,
    spec_path: str = "", spec_digest: str = "",
) -> None:
    data = {
        "title": title, "summary": summary,
        "key_decisions": key_decisions or [],
        "files_changed": files_changed or [],
        "verification": verification,
        "known_limitations": known_limitations or [],
        "spec_path": spec_path, "spec_digest": spec_digest,
    }
    md = f"# Claude Implementation Summary\n\n"
    md += f"## What Was Done\n\n{summary or '<!-- description -->'}\n\n"
    md += f"## Key Decisions\n\n"
    for d in (key_decisions or []):
        md += f"- {d}\n"
    if not key_decisions:
        md += "<!-- decisions -->\n"
    md += f"\n## Changed Files\n\n"
    for f in (files_changed or []):
        md += f"- {f}\n"
    if not files_changed:
        md += "<!-- files -->\n"
    md += f"\n## Testing\n\n{verification or '<!-- how verified -->'}\n"
    if known_limitations:
        md += f"\n## Known Limitations\n\n"
        for l in known_limitations:
            md += f"- {l}\n"
    write_dual(cycle_dir, "implementation_summary", data, md)
    (cycle_dir / "claude-implementation-summary.md").write_text(md)
