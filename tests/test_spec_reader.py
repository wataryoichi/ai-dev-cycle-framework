"""Tests for spec reader."""

from __future__ import annotations

from pathlib import Path

import pytest

from dev_cycle.spec_reader import find_spec, read_spec, empty_spec, _split_frontmatter, _extract_summary


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / "docs").mkdir()
    return tmp_path


class TestFindSpec:
    def test_default_path(self, project: Path) -> None:
        (project / "docs" / "spec.md").write_text("# Spec\n\nBuild X.\n")
        result = find_spec(project)
        assert result is not None
        assert result.name == "spec.md"

    def test_explicit_path(self, project: Path) -> None:
        (project / "custom.md").write_text("# Custom\n")
        result = find_spec(project, "custom.md")
        assert result is not None
        assert result.name == "custom.md"

    def test_missing_returns_none(self, project: Path) -> None:
        assert find_spec(project) is None

    def test_explicit_missing_returns_none(self, project: Path) -> None:
        assert find_spec(project, "nonexistent.md") is None


class TestReadSpec:
    def test_reads_body(self, project: Path) -> None:
        spec = project / "docs" / "spec.md"
        spec.write_text("# My Spec\n\nBuild a hello world app.\n\n## Scope\n\nSmall.\n")
        result = read_spec(spec)
        assert result["present"]
        assert "hello world" in result["summary"]
        assert result["digest"]
        assert len(result["digest"]) == 12

    def test_reads_frontmatter(self, project: Path) -> None:
        spec = project / "docs" / "spec.md"
        spec.write_text("---\ntitle: My Feature\ngoal: Build it\n---\n\n# Overview\n\nDetails.\n")
        result = read_spec(spec)
        assert result["frontmatter"]["title"] == "My Feature"
        assert result["frontmatter"]["goal"] == "Build it"
        assert "Details" in result["body"]

    def test_no_frontmatter(self, project: Path) -> None:
        spec = project / "docs" / "spec.md"
        spec.write_text("# Just a doc\n\nContent here.\n")
        result = read_spec(spec)
        assert result["frontmatter"] == {}
        assert "Content here" in result["summary"]


class TestEmptySpec:
    def test_empty_spec(self) -> None:
        s = empty_spec()
        assert not s["present"]
        assert s["digest"] == ""
        assert s["summary"] == ""


class TestSplitFrontmatter:
    def test_with_frontmatter(self) -> None:
        fm, body = _split_frontmatter("---\nkey: val\n---\n\nBody text.")
        assert fm["key"] == "val"
        assert "Body text" in body

    def test_without_frontmatter(self) -> None:
        fm, body = _split_frontmatter("# Just markdown\n\nContent.")
        assert fm == {}
        assert "Just markdown" in body


class TestExtractSummary:
    def test_basic(self) -> None:
        s = _extract_summary("# Title\n\nFirst paragraph.\n\nSecond paragraph.")
        assert "First paragraph" in s

    def test_skips_comments(self) -> None:
        s = _extract_summary("<!-- hidden -->\n\nVisible text.")
        assert "Visible" in s
        assert "hidden" not in s

    def test_max_length(self) -> None:
        long = "A" * 1000
        s = _extract_summary(long, max_len=100)
        assert len(s) <= 100
