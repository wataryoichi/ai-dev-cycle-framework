"""Dual output — write both Markdown and JSON for cycle records.

Markdown uses locale-aware labels. JSON keys stay English.
"""

from __future__ import annotations

import json
from pathlib import Path

from .i18n import get_labels


def write_dual(cycle_dir: Path, name: str, data: dict, md_content: str) -> None:
    (cycle_dir / f"{name}.json").write_text(json.dumps(data, indent=2) + "\n")
    (cycle_dir / f"{name}.md").write_text(md_content)


def write_request(cycle_dir: Path, title: str, version: str,
                  goal: str = "", context: str = "", scope: str = "", notes: str = "",
                  spec: dict | None = None, lang: str = "en") -> None:
    L = get_labels(lang)
    data = {"title": title, "version": version, "goal": goal,
            "context": context, "scope": scope, "notes": notes, "lang": lang}
    if spec and spec.get("present"):
        data["spec_path"] = spec.get("path", "")
        data["spec_present"] = True
        data["spec_digest"] = spec.get("digest", "")
        data["spec_summary"] = spec.get("summary", "")
        data["spec_constraints"] = spec.get("constraints", [])
        data["spec_expected_outputs"] = spec.get("expected_outputs", [])

    md = (
        f"# {L['request_title']} — {title}\n\n"
        f"**Version:** {version}\n\n"
        f"## {L['goal']}\n\n{goal or L['placeholder_goal']}\n\n"
        f"## {L['context']}\n\n{context or L['placeholder_context']}\n\n"
        f"## {L['scope']}\n\n{scope or L['placeholder_scope']}\n\n"
        f"## {L['notes']}\n\n{notes or L['placeholder_notes']}\n"
    )
    if spec and spec.get("present"):
        md += f"\n## {L['spec']}\n\n"
        md += f"- **Path:** `{spec.get('path', '')}`\n"
        md += f"- **Digest:** `{spec.get('digest', '')}`\n"
        if spec.get("summary"):
            md += f"\n{spec['summary'][:300]}\n"
        if spec.get("constraints"):
            md += f"\n### {L['constraints']}\n"
            for c in spec["constraints"][:10]:
                md += f"- {c}\n"
        if spec.get("expected_outputs"):
            md += f"\n### {L['expected_outputs']}\n"
            for o in spec["expected_outputs"][:10]:
                md += f"- {o}\n"

    write_dual(cycle_dir, "request", data, md)


def write_review(cycle_dir: Path, summary: str = "", high: list[str] | None = None,
                 medium: list[str] | None = None, low: list[str] | None = None,
                 raw: str = "", lang: str = "en") -> None:
    L = get_labels(lang)
    data = {"summary": summary, "high": high or [], "medium": medium or [],
            "low": low or [], "raw": raw}
    from .review_importer import format_review
    md = format_review(data)
    write_dual(cycle_dir, "review", data, md)
    (cycle_dir / "codex-review.md").write_text(md)


def write_followup(cycle_dir: Path, accepted: list[dict] | None = None,
                   deferred: list[dict] | None = None,
                   rejected: list[dict] | None = None, notes: str = "",
                   lang: str = "en") -> None:
    L = get_labels(lang)
    data = {"accepted": accepted or [], "deferred": deferred or [],
            "rejected": rejected or [], "notes": notes}
    lines = [f"# {L['followup_title']}\n\n## {L['accepted']}"]
    for item in (accepted or []):
        lines.append(f"- [{item.get('severity', '?')}] {item.get('finding', '')}: {item.get('action', '<!-- action -->')}")
    lines.extend([f"\n## {L['deferred']}"])
    for item in (deferred or []):
        lines.append(f"- {item.get('finding', '')}: {item.get('reason', '')}")
    lines.extend([f"\n## {L['rejected']}"])
    for item in (rejected or []):
        lines.append(f"- {item.get('finding', '')}: {item.get('reason', '')}")
    if notes:
        lines.extend([f"\n## {L['additional_notes']}\n{notes}"])
    lines.append("")
    md = "\n".join(lines)
    write_dual(cycle_dir, "followup", data, md)
    (cycle_dir / "codex-followup.md").write_text(md)


def write_final_summary(cycle_dir: Path, overview: str = "", changes: list[str] | None = None,
                        verification: str = "", remaining: list[str] | None = None,
                        lang: str = "en") -> None:
    L = get_labels(lang)
    data = {"overview": overview, "changes": changes or [],
            "verification": verification, "remaining": remaining or []}
    md = f"# {L['final_title']}\n\n## {L['overview']}\n{overview or '<!-- -->'}\n\n## {L['changes']}\n"
    for c in (changes or []):
        md += f"- {c}\n"
    md += f"\n## {L['verification']}\n{verification or '<!-- -->'}\n\n## {L['remaining_issues']}\n"
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
    lang: str = "en",
) -> None:
    L = get_labels(lang)
    data = {
        "title": title, "summary": summary,
        "key_decisions": key_decisions or [],
        "files_changed": files_changed or [],
        "verification": verification,
        "known_limitations": known_limitations or [],
        "spec_path": spec_path, "spec_digest": spec_digest,
    }
    md = f"# {L['impl_title']}\n\n## {L['what_was_done']}\n\n{summary or '<!-- -->'}\n\n"
    md += f"## {L['key_decisions']}\n\n"
    for d in (key_decisions or []):
        md += f"- {d}\n"
    md += f"\n## {L['changed_files']}\n\n"
    for f in (files_changed or []):
        md += f"- {f}\n"
    md += f"\n## {L['testing']}\n\n{verification or '<!-- -->'}\n"
    if known_limitations:
        md += f"\n## {L['known_limitations']}\n\n"
        for l in known_limitations:
            md += f"- {l}\n"
    write_dual(cycle_dir, "implementation_summary", data, md)
    (cycle_dir / "claude-implementation-summary.md").write_text(md)
