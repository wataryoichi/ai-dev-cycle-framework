"""Tests for review orchestration — prepare and finalize review."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dev_cycle.config import Config
from dev_cycle.cycle import _read_meta, _update_phase, _write_meta
from dev_cycle.review_importer import import_review
from dev_cycle.review_orchestrator import finalize_review, prepare_review
from tests.conftest import SAMPLE_REVIEW_UNSTRUCTURED


class TestPrepareReview:
    def test_sets_phase_to_review_pending(self, cfg: Config, cycle_dir: Path) -> None:
        info = prepare_review(cfg, cycle_dir)
        meta = _read_meta(cycle_dir)
        assert meta["phase"] == "review_pending"

    def test_returns_cycle_info(self, cfg: Config, cycle_dir: Path) -> None:
        info = prepare_review(cfg, cycle_dir)
        assert info["cycle_id"] == _read_meta(cycle_dir)["cycle_id"]
        assert info["version"] == "v0.1.0"
        assert info["title"] == "test cycle"
        assert info["phase"] == "review_pending"
        assert "branch" in info
        assert "review_file" in info
        assert "recent_commits" in info

    def test_review_file_exists(self, cfg: Config, cycle_dir: Path) -> None:
        info = prepare_review(cfg, cycle_dir)
        assert Path(info["review_file"]).exists()

    def test_idempotent(self, cfg: Config, cycle_dir: Path) -> None:
        prepare_review(cfg, cycle_dir)
        info = prepare_review(cfg, cycle_dir)
        assert info["phase"] == "review_pending"


class TestFinalizeReview:
    def test_sets_phase_to_review_done(self, cfg: Config, cycle_dir: Path) -> None:
        prepare_review(cfg, cycle_dir)
        import_review(cycle_dir, SAMPLE_REVIEW_UNSTRUCTURED)
        finalize_review(cfg, cycle_dir)
        meta = _read_meta(cycle_dir)
        assert meta["phase"] == "review_done"

    def test_warns_if_review_empty(self, cfg: Config, cycle_dir: Path) -> None:
        warnings = finalize_review(cfg, cycle_dir)
        assert any("empty" in w.lower() or "still" in w.lower() for w in warnings)

    def test_no_warnings_if_review_filled(self, cfg: Config, cycle_dir: Path) -> None:
        import_review(cycle_dir, SAMPLE_REVIEW_UNSTRUCTURED)
        warnings = finalize_review(cfg, cycle_dir)
        assert warnings == []

    def test_followup_template_ready(self, cfg: Config, cycle_dir: Path) -> None:
        finalize_review(cfg, cycle_dir)
        followup = cycle_dir / "codex-followup.md"
        assert followup.exists()
