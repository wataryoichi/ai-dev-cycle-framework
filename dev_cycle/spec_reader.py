"""Read and parse spec files into a structured contract.

Supports optional YAML-like frontmatter and heuristic extraction of
constraints, expected outputs, acceptance criteria, and non-goals from
the Markdown body.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

DEFAULT_SPEC_PATH = "docs/spec.md"


def find_spec(project_root: Path, spec_arg: str | None = None) -> Path | None:
    """Find spec file. Priority: --spec arg > docs/spec.md > None."""
    if spec_arg:
        p = Path(spec_arg)
        if not p.is_absolute():
            p = project_root / p
        return p if p.exists() else None
    default = project_root / DEFAULT_SPEC_PATH
    return default if default.exists() else None


def read_spec(spec_path: Path) -> dict:
    """Read spec file and return a structured contract dict."""
    content = spec_path.read_text()
    frontmatter, body = _split_frontmatter(content)
    digest = hashlib.sha256(content.encode()).hexdigest()[:12]

    # Extract structured fields
    title = frontmatter.get("title", _extract_title(body))
    summary = _extract_summary(body)
    constraints = _extract_section(body, "constraints")
    expected_outputs = _extract_section(body, "expected.?outputs?|output.?expectations?")
    acceptance_criteria = _extract_section(body, "acceptance.?criteria")
    non_goals = _extract_section(body, "non.?goals?")

    return {
        "path": str(spec_path),
        "present": True,
        "digest": digest,
        "title": title,
        "summary": summary,
        "constraints": constraints,
        "expected_outputs": expected_outputs,
        "acceptance_criteria": acceptance_criteria,
        "non_goals": non_goals,
        "frontmatter": frontmatter,
        "body": body,
        "full_text": content,
    }


def empty_spec() -> dict:
    """Return a spec-absent placeholder."""
    return {
        "path": "", "present": False, "digest": "", "title": "",
        "summary": "", "constraints": [], "expected_outputs": [],
        "acceptance_criteria": [], "non_goals": [],
        "frontmatter": {}, "body": "", "full_text": "",
    }


def load_spec_from_meta(cycle_dir: Path) -> dict | None:
    """Load spec from meta.json spec_path. Returns None if not available."""
    import json
    meta_path = cycle_dir / "meta.json"
    if not meta_path.exists():
        return None
    meta = json.loads(meta_path.read_text())
    spec_path = meta.get("spec_path", "")
    if not spec_path:
        return None
    p = Path(spec_path)
    if not p.exists():
        return None
    try:
        return read_spec(p)
    except Exception:
        return None


# ── Internal helpers ─────────────────────────────────────────

def _split_frontmatter(content: str) -> tuple[dict, str]:
    if not content.startswith("---"):
        return {}, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    fm = {}
    for line in parts[1].strip().split("\n"):
        if ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip()
    return fm, parts[2].strip()


def _extract_title(body: str) -> str:
    for line in body.split("\n"):
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def _extract_summary(body: str, max_len: int = 500) -> str:
    lines = body.split("\n")
    parts = []
    count = 0
    for line in lines:
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("<!--"):
            continue
        parts.append(s)
        count += len(s)
        if count >= max_len:
            break
    return " ".join(parts)[:max_len]


def _extract_section(body: str, pattern: str) -> list[str]:
    """Extract bullet items from a section matching the header pattern."""
    header_re = re.compile(rf"^##\s+{pattern}", re.IGNORECASE | re.MULTILINE)
    match = header_re.search(body)
    if not match:
        return []

    # Get text until next ## header or end
    start = match.end()
    next_header = re.search(r"^##\s+", body[start:], re.MULTILINE)
    section = body[start:start + next_header.start()] if next_header else body[start:]

    items = []
    for line in section.split("\n"):
        s = line.strip()
        if s.startswith("- ") or s.startswith("* "):
            content = s[2:].strip()
            if content and not content.startswith("<!--"):
                items.append(content)
    return items
