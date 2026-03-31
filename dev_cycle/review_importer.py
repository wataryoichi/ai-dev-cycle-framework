"""Import Codex review output into a cycle's codex-review.md."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from .cycle import _read_meta, _update_phase, _write_meta


def import_review(cycle_dir: Path, raw_text: str) -> Path:
    """Import review text into codex-review.md and update phase.

    Returns the path to the updated review file.
    """
    review_path = cycle_dir / "codex-review.md"
    parsed = parse_review(raw_text)
    review_path.write_text(format_review(parsed))

    meta = _read_meta(cycle_dir)
    _update_phase(meta, "review_imported")
    _write_meta(cycle_dir, meta)

    return review_path


def read_input(from_file: str | None, text: str | None) -> str:
    """Read review text from file, argument, or stdin.

    Priority: --text > --from-file > stdin pipe.
    Exits with code 1 if no input is available.
    """
    if text:
        return text
    if from_file:
        p = Path(from_file)
        if not p.exists():
            print(f"Error: file not found: {from_file}", file=sys.stderr)
            sys.exit(1)
        content = p.read_text()
        if not content.strip():
            print(f"Error: file is empty: {from_file}", file=sys.stderr)
            sys.exit(1)
        return content
    if not sys.stdin.isatty():
        content = sys.stdin.read()
        if not content.strip():
            print("Error: stdin is empty — pipe review output or use --from-file", file=sys.stderr)
            sys.exit(1)
        return content
    print("Error: provide review input via one of:", file=sys.stderr)
    print("  --from-file codex-output.txt", file=sys.stderr)
    print("  --text '...'", file=sys.stderr)
    print("  cat codex-output.txt | <command>", file=sys.stderr)
    sys.exit(1)


def parse_review(raw: str) -> dict:
    """Parse raw Codex output into structured review data.

    Uses simple heuristics — not a full parser. Handles:
    - Already structured markdown (pass-through)
    - Unstructured text (wrapped into Raw Notes)
    - Bullet lists (attempt severity classification)
    """
    raw = raw.strip()
    if not raw:
        return {"summary": "", "high": [], "medium": [], "low": [], "raw": ""}

    # If it already has our structure, extract sections
    if "## Findings" in raw or "### High" in raw:
        return _parse_structured(raw)

    # Try to extract bullet points and classify
    return _parse_unstructured(raw)


def _parse_structured(text: str) -> dict:
    """Extract from already-structured markdown."""
    result = {"summary": "", "high": [], "medium": [], "low": [], "raw": ""}

    # Extract summary
    m = re.search(r"## Summary\s*\n(.*?)(?=\n##|\Z)", text, re.DOTALL)
    if m:
        result["summary"] = m.group(1).strip()

    # Extract severity sections
    for level in ("high", "medium", "low"):
        pattern = rf"###\s*{level.capitalize()}\s*\n(.*?)(?=\n###|\n##|\Z)"
        m = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if m:
            items = _extract_bullets(m.group(1))
            result[level] = items

    # Extract raw notes
    m = re.search(r"## Raw Notes\s*\n(.*?)(?=\n##|\Z)", text, re.DOTALL)
    if m:
        result["raw"] = m.group(1).strip()

    return result


def _parse_unstructured(text: str) -> dict:
    """Parse unstructured review text with heuristic classification."""
    result = {"summary": "", "high": [], "medium": [], "low": [], "raw": text}

    lines = text.split("\n")
    bullets = _extract_bullets(text)

    if not bullets:
        # No structure found — everything goes to raw, first line as summary
        result["summary"] = lines[0][:200] if lines else ""
        return result

    # Heuristic: classify by keywords
    high_keywords = re.compile(
        r"\b(critical|severe|security|vulnerability|crash|data.?loss|break|bug|error|fail|wrong)\b",
        re.IGNORECASE,
    )
    medium_keywords = re.compile(
        r"\b(should|improve|refactor|missing|consider|unclear|inconsist|edge.?case|handle)\b",
        re.IGNORECASE,
    )

    for bullet in bullets:
        if high_keywords.search(bullet):
            result["high"].append(bullet)
        elif medium_keywords.search(bullet):
            result["medium"].append(bullet)
        else:
            result["low"].append(bullet)

    # First non-bullet paragraph as summary
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("-") and not stripped.startswith("*") and not stripped.startswith("#"):
            result["summary"] = stripped[:200]
            break

    return result


def _extract_bullets(text: str) -> list[str]:
    """Extract bullet points from text."""
    bullets = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("- ") or stripped.startswith("* "):
            content = stripped[2:].strip()
            if content and not content.startswith("<!--"):
                bullets.append(content)
    return bullets


def format_review(parsed: dict) -> str:
    """Format parsed review data into the standard template."""
    lines = [
        "# Codex Review",
        "",
        "## Reviewer",
        "Codex",
        "",
        "## Summary",
        parsed.get("summary", "") or "<!-- Overall review summary -->",
        "",
        "## Findings",
        "",
        "### High",
    ]

    if parsed.get("high"):
        for item in parsed["high"]:
            lines.append(f"- {item}")
    else:
        lines.append("- (none)")

    lines.extend(["", "### Medium"])
    if parsed.get("medium"):
        for item in parsed["medium"]:
            lines.append(f"- {item}")
    else:
        lines.append("- (none)")

    lines.extend(["", "### Low"])
    if parsed.get("low"):
        for item in parsed["low"]:
            lines.append(f"- {item}")
    else:
        lines.append("- (none)")

    lines.extend(["", "## Raw Notes"])
    if parsed.get("raw"):
        lines.append(parsed["raw"])
    else:
        lines.append("<!-- Original review output -->")

    lines.append("")
    return "\n".join(lines)


def count_findings(cycle_dir: Path) -> dict[str, int]:
    """Count findings in codex-review.md by severity."""
    review_path = cycle_dir / "codex-review.md"
    if not review_path.exists():
        return {"high": 0, "medium": 0, "low": 0, "total": 0}
    parsed = parse_review(review_path.read_text())
    counts = {}
    total = 0
    for level in ("high", "medium", "low"):
        items = [i for i in parsed.get(level, []) if i != "(none)"]
        counts[level] = len(items)
        total += len(items)
    counts["total"] = total
    return counts


def generate_followup_draft(cycle_dir: Path) -> str:
    """Generate a followup draft from codex-review.md findings."""
    review_path = cycle_dir / "codex-review.md"
    if not review_path.exists():
        return ""

    parsed = parse_review(review_path.read_text())
    lines = ["# Codex Follow-up", "", "## Accepted"]

    all_findings = []
    for level in ("high", "medium", "low"):
        for item in parsed.get(level, []):
            if item != "(none)":
                all_findings.append((level, item))

    if all_findings:
        for level, item in all_findings:
            lines.append(f"- [{level.upper()}] {item}: <!-- action taken -->")
    else:
        lines.append("<!-- - Finding: what was changed -->")

    lines.extend([
        "",
        "## Deferred",
        "<!-- - Finding: reason for deferral -->",
        "",
        "## Rejected",
        "<!-- - Finding: reason for rejection -->",
        "",
        "## Additional Notes",
        "<!-- Any extra context -->",
        "",
    ])
    return "\n".join(lines)
