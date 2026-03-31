"""Tests for review import, parsing, and followup generation."""

from __future__ import annotations

from pathlib import Path

import pytest

from dev_cycle.review_importer import (
    count_findings,
    format_review,
    generate_followup_draft,
    import_review,
    parse_review,
)
from tests.conftest import SAMPLE_REVIEW_STRUCTURED, SAMPLE_REVIEW_UNSTRUCTURED


class TestParseReview:
    def test_empty_input(self) -> None:
        result = parse_review("")
        assert result["high"] == []
        assert result["medium"] == []
        assert result["low"] == []
        assert result["summary"] == ""

    def test_unstructured_classifies_by_severity(self) -> None:
        result = parse_review(SAMPLE_REVIEW_UNSTRUCTURED)
        assert len(result["high"]) >= 1  # "Critical" triggers high
        assert len(result["medium"]) >= 1  # "Should" triggers medium
        assert result["raw"] == SAMPLE_REVIEW_UNSTRUCTURED.strip()

    def test_structured_extracts_sections(self) -> None:
        result = parse_review(SAMPLE_REVIEW_STRUCTURED)
        assert result["summary"].startswith("Solid")
        assert len(result["high"]) == 1
        assert len(result["medium"]) == 2
        assert len(result["low"]) == 1
        assert "2026-03-31" in result["raw"]

    def test_unstructured_with_no_bullets(self) -> None:
        result = parse_review("Just a paragraph of text.\nNo bullets here.")
        assert result["summary"] == "Just a paragraph of text."
        assert result["raw"] == "Just a paragraph of text.\nNo bullets here."


class TestFormatReview:
    def test_formats_with_findings(self) -> None:
        parsed = {
            "summary": "Good code",
            "high": ["Bug A"],
            "medium": ["Issue B", "Issue C"],
            "low": [],
            "raw": "raw text",
        }
        output = format_review(parsed)
        assert "# Codex Review" in output
        assert "## Summary" in output
        assert "Good code" in output
        assert "### High" in output
        assert "- Bug A" in output
        assert "### Medium" in output
        assert "- Issue B" in output
        assert "### Low" in output
        assert "- (none)" in output
        assert "## Raw Notes" in output
        assert "raw text" in output

    def test_formats_empty_findings(self) -> None:
        parsed = {"summary": "", "high": [], "medium": [], "low": [], "raw": ""}
        output = format_review(parsed)
        assert output.count("(none)") == 3


class TestImportReview:
    def test_imports_and_updates_phase(self, cycle_dir: Path) -> None:
        import json
        review_path = import_review(cycle_dir, SAMPLE_REVIEW_UNSTRUCTURED)
        assert review_path.exists()
        assert "# Codex Review" in review_path.read_text()

        meta = json.loads((cycle_dir / "meta.json").read_text())
        assert meta["phase"] == "review_imported"

    def test_imports_structured_review(self, cycle_dir: Path) -> None:
        review_path = import_review(cycle_dir, SAMPLE_REVIEW_STRUCTURED)
        content = review_path.read_text()
        assert "Missing input validation" in content


class TestCountFindings:
    def test_no_review_file(self, cycle_dir: Path) -> None:
        (cycle_dir / "codex-review.md").unlink()
        counts = count_findings(cycle_dir)
        assert counts == {"high": 0, "medium": 0, "low": 0, "total": 0}

    def test_counts_from_imported_review(self, cycle_dir: Path) -> None:
        import_review(cycle_dir, SAMPLE_REVIEW_STRUCTURED)
        counts = count_findings(cycle_dir)
        assert counts["high"] == 1
        assert counts["medium"] == 2
        assert counts["low"] == 1
        assert counts["total"] == 4


class TestGenerateFollowupDraft:
    def test_no_review(self, cycle_dir: Path) -> None:
        (cycle_dir / "codex-review.md").unlink()
        assert generate_followup_draft(cycle_dir) == ""

    def test_generates_from_review(self, cycle_dir: Path) -> None:
        import_review(cycle_dir, SAMPLE_REVIEW_STRUCTURED)
        draft = generate_followup_draft(cycle_dir)
        assert "# Codex Follow-up" in draft
        assert "## Accepted" in draft
        assert "[HIGH]" in draft
        assert "[MEDIUM]" in draft
        assert "[LOW]" in draft

    def test_empty_findings_no_tags(self, cycle_dir: Path) -> None:
        import_review(cycle_dir, "Looks great, no issues found.")
        draft = generate_followup_draft(cycle_dir)
        assert "# Codex Follow-up" in draft
