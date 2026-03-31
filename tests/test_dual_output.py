"""Tests for dual Markdown + JSON output."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dev_cycle.dual_output import write_dual, write_request, write_review, write_followup, write_final_summary


@pytest.fixture
def cycle_dir(tmp_path: Path) -> Path:
    d = tmp_path / "cycle"
    d.mkdir()
    return d


class TestWriteDual:
    def test_creates_both_files(self, cycle_dir) -> None:
        write_dual(cycle_dir, "test", {"key": "val"}, "# Test\n\nContent.\n")
        assert (cycle_dir / "test.json").exists()
        assert (cycle_dir / "test.md").exists()

    def test_json_is_valid(self, cycle_dir) -> None:
        write_dual(cycle_dir, "test", {"a": 1}, "# Test\n")
        data = json.loads((cycle_dir / "test.json").read_text())
        assert data["a"] == 1


class TestWriteRequest:
    def test_creates_files(self, cycle_dir) -> None:
        write_request(cycle_dir, "my feature", "v1.0.0", goal="Build it")
        assert (cycle_dir / "request.json").exists()
        assert (cycle_dir / "request.md").exists()
        data = json.loads((cycle_dir / "request.json").read_text())
        assert data["title"] == "my feature"
        assert data["goal"] == "Build it"
        md = (cycle_dir / "request.md").read_text()
        assert "my feature" in md
        assert "Build it" in md


class TestWriteReview:
    def test_creates_files(self, cycle_dir) -> None:
        write_review(cycle_dir, summary="Good", high=["Bug A"], medium=["Issue B"])
        assert (cycle_dir / "review.json").exists()
        assert (cycle_dir / "review.md").exists()
        assert (cycle_dir / "codex-review.md").exists()  # backward compat
        data = json.loads((cycle_dir / "review.json").read_text())
        assert data["high"] == ["Bug A"]


class TestWriteFollowup:
    def test_creates_files(self, cycle_dir) -> None:
        write_followup(cycle_dir, accepted=[{"severity": "HIGH", "finding": "Bug", "action": "fixed"}])
        assert (cycle_dir / "followup.json").exists()
        assert (cycle_dir / "followup.md").exists()
        data = json.loads((cycle_dir / "followup.json").read_text())
        assert len(data["accepted"]) == 1


class TestWriteFinalSummary:
    def test_creates_files(self, cycle_dir) -> None:
        write_final_summary(cycle_dir, overview="Done.", changes=["foo.py"], verification="Tests pass.")
        assert (cycle_dir / "final_summary.json").exists()
        assert (cycle_dir / "final_summary.md").exists()
        assert (cycle_dir / "final-summary.md").exists()  # backward compat
        data = json.loads((cycle_dir / "final_summary.json").read_text())
        assert data["overview"] == "Done."
