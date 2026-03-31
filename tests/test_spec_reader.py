"""Tests for spec reader — find, read, parse, extract."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dev_cycle.spec_reader import (
    find_spec, read_spec, empty_spec, load_spec_from_meta,
    _split_frontmatter, _extract_summary, _extract_section,
)


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / "docs").mkdir()
    return tmp_path


RICH_SPEC = """\
---
title: Build Widget
goal: Create a reusable widget
---

# Widget Spec

Build a widget that handles user input.

## Constraints
- Must be pure Python
- No external dependencies
- Must handle Unicode

## Expected Outputs
- widget.py with Widget class
- tests/test_widget.py

## Acceptance Criteria
- Widget renders correctly
- Handles empty input gracefully
- Passes all unit tests

## Non-goals
- GUI support
- Database integration
"""


class TestFindSpec:
    def test_default_path(self, project: Path) -> None:
        (project / "docs" / "spec.md").write_text("# Spec\n")
        assert find_spec(project) is not None

    def test_explicit_path(self, project: Path) -> None:
        (project / "custom.md").write_text("# Custom\n")
        assert find_spec(project, "custom.md") is not None

    def test_missing(self, project: Path) -> None:
        assert find_spec(project) is None

    def test_explicit_missing(self, project: Path) -> None:
        assert find_spec(project, "nope.md") is None


class TestReadSpec:
    def test_basic(self, project: Path) -> None:
        spec = project / "docs" / "spec.md"
        spec.write_text("# My Spec\n\nBuild a hello world.\n")
        result = read_spec(spec)
        assert result["present"]
        assert "hello world" in result["summary"]
        assert len(result["digest"]) == 12

    def test_rich_spec(self, project: Path) -> None:
        spec = project / "docs" / "spec.md"
        spec.write_text(RICH_SPEC)
        result = read_spec(spec)
        assert result["title"] == "Build Widget"
        assert result["frontmatter"]["goal"] == "Create a reusable widget"
        assert len(result["constraints"]) == 3
        assert "pure Python" in result["constraints"][0]
        assert len(result["expected_outputs"]) == 2
        assert len(result["acceptance_criteria"]) == 3
        assert len(result["non_goals"]) == 2

    def test_no_frontmatter(self, project: Path) -> None:
        spec = project / "docs" / "spec.md"
        spec.write_text("# Just a doc\n\nContent.\n")
        result = read_spec(spec)
        assert result["frontmatter"] == {}
        assert result["title"] == "Just a doc"


class TestEmptySpec:
    def test_empty(self) -> None:
        s = empty_spec()
        assert not s["present"]
        assert s["constraints"] == []
        assert s["acceptance_criteria"] == []


class TestLoadSpecFromMeta:
    def test_loads_when_present(self, project: Path) -> None:
        spec = project / "docs" / "spec.md"
        spec.write_text(RICH_SPEC)
        cycle = project / "cycle"
        cycle.mkdir()
        (cycle / "meta.json").write_text(json.dumps({"spec_path": str(spec)}))
        result = load_spec_from_meta(cycle)
        assert result is not None
        assert result["present"]
        assert len(result["constraints"]) == 3

    def test_returns_none_when_missing(self, project: Path) -> None:
        cycle = project / "cycle"
        cycle.mkdir()
        (cycle / "meta.json").write_text(json.dumps({}))
        assert load_spec_from_meta(cycle) is None

    def test_returns_none_when_file_gone(self, project: Path) -> None:
        cycle = project / "cycle"
        cycle.mkdir()
        (cycle / "meta.json").write_text(json.dumps({"spec_path": "/nonexistent.md"}))
        assert load_spec_from_meta(cycle) is None


class TestExtractSection:
    def test_constraints(self) -> None:
        items = _extract_section(RICH_SPEC, "constraints")
        assert len(items) == 3

    def test_expected_outputs(self) -> None:
        items = _extract_section(RICH_SPEC, "expected.?outputs?")
        assert len(items) == 2

    def test_acceptance_criteria(self) -> None:
        items = _extract_section(RICH_SPEC, "acceptance.?criteria")
        assert len(items) == 3

    def test_non_goals(self) -> None:
        items = _extract_section(RICH_SPEC, "non.?goals?")
        assert len(items) == 2

    def test_missing_section(self) -> None:
        assert _extract_section("# Nothing here\n", "constraints") == []


class TestSplitFrontmatter:
    def test_with(self) -> None:
        fm, body = _split_frontmatter("---\nkey: val\n---\n\nBody.")
        assert fm["key"] == "val"
        assert "Body" in body

    def test_without(self) -> None:
        fm, body = _split_frontmatter("# Just markdown\n")
        assert fm == {}


class TestExtractSummary:
    def test_basic(self) -> None:
        assert "First" in _extract_summary("# T\n\nFirst paragraph.\n")

    def test_max_len(self) -> None:
        assert len(_extract_summary("A" * 1000, max_len=100)) <= 100
