"""Read and parse spec files (docs/spec.md or custom path)."""

from __future__ import annotations

import hashlib
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
    """Read spec file and return structured data."""
    content = spec_path.read_text()
    frontmatter, body = _split_frontmatter(content)
    digest = hashlib.sha256(content.encode()).hexdigest()[:12]
    summary = _extract_summary(body)

    return {
        "path": str(spec_path),
        "present": True,
        "digest": digest,
        "summary": summary,
        "frontmatter": frontmatter,
        "body": body,
        "full_text": content,
    }


def empty_spec() -> dict:
    """Return a spec-absent placeholder."""
    return {
        "path": "",
        "present": False,
        "digest": "",
        "summary": "",
        "frontmatter": {},
        "body": "",
        "full_text": "",
    }


def _split_frontmatter(content: str) -> tuple[dict, str]:
    """Split optional YAML frontmatter from body."""
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    fm_text = parts[1].strip()
    body = parts[2].strip()

    # Simple key: value parsing (no YAML dependency)
    fm = {}
    for line in fm_text.split("\n"):
        if ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip()
    return fm, body


def _extract_summary(body: str, max_len: int = 500) -> str:
    """Extract a short summary from the spec body."""
    lines = body.split("\n")
    summary_lines = []
    char_count = 0

    for line in lines:
        stripped = line.strip()
        # Skip headers and empty lines for summary
        if stripped.startswith("#") or not stripped:
            continue
        if stripped.startswith("<!--"):
            continue
        summary_lines.append(stripped)
        char_count += len(stripped)
        if char_count >= max_len:
            break

    return " ".join(summary_lines)[:max_len]
