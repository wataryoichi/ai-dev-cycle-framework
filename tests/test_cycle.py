"""Tests for cycle operations — create, phase, check, finalize."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dev_cycle.config import Config
from dev_cycle.cycle import (
    PHASES,
    NoCyclesError,
    StrictFinalizeError,
    _detect_rereview_hint,
    _is_placeholder,
    _read_meta,
    _resolve_cycle_dir,
    _update_phase,
    _write_meta,
    check_cycle,
    find_latest_cycle,
    finalize_cycle,
    next_step,
    start_cycle,
)


class TestStartCycle:
    def test_creates_directory_with_meta(self, cfg: Config) -> None:
        cycle_dir = start_cycle(cfg, "v0.1.0", "test feature")
        assert cycle_dir.exists()
        meta = json.loads((cycle_dir / "meta.json").read_text())
        assert meta["version"] == "v0.1.0"
        assert meta["title"] == "test feature"
        assert meta["phase"] == "started"
        assert meta["status"] == "started"

    def test_creates_all_template_files(self, cfg: Config) -> None:
        cycle_dir = start_cycle(cfg, "v0.1.0", "test")
        expected = [
            "meta.json", "request.md", "claude-implementation-summary.md",
            "codex-review.md", "codex-followup.md", "final-summary.md",
            "self-application-notes.md",
        ]
        for f in expected:
            assert (cycle_dir / f).exists(), f"Missing: {f}"

    def test_templates_are_placeholders(self, cfg: Config) -> None:
        cycle_dir = start_cycle(cfg, "v0.1.0", "test")
        for f in ["claude-implementation-summary.md", "codex-review.md",
                   "codex-followup.md", "final-summary.md"]:
            assert _is_placeholder(cycle_dir / f), f"{f} should be a placeholder"

    def test_cycle_id_format(self, cfg: Config) -> None:
        cycle_dir = start_cycle(cfg, "v0.2.0", "my cool feature")
        meta = _read_meta(cycle_dir)
        assert meta["cycle_id"].startswith("v0.2.0_")
        assert "my-cool-feature" in meta["cycle_id"]


class TestPhaseTransition:
    def test_update_phase_started(self) -> None:
        meta = {"status": "in_progress", "phase": "review_done"}
        _update_phase(meta, "started")
        assert meta["phase"] == "started"
        assert meta["status"] == "started"

    def test_update_phase_completed(self) -> None:
        meta = {"status": "in_progress", "phase": "followup_done"}
        _update_phase(meta, "completed")
        assert meta["phase"] == "completed"
        assert meta["status"] == "completed"

    def test_update_phase_in_progress(self) -> None:
        meta = {"status": "started", "phase": "started"}
        _update_phase(meta, "review_pending")
        assert meta["phase"] == "review_pending"
        assert meta["status"] == "in_progress"

    def test_all_phases_valid(self) -> None:
        for phase in PHASES:
            meta = {"status": "started", "phase": "started"}
            _update_phase(meta, phase)
            assert meta["phase"] == phase


class TestIsPlaceholder:
    def test_nonexistent_file(self, tmp_path: Path) -> None:
        assert _is_placeholder(tmp_path / "nope.md")

    def test_empty_file(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.md"
        f.write_text("")
        assert _is_placeholder(f)

    def test_only_headers(self, tmp_path: Path) -> None:
        f = tmp_path / "headers.md"
        f.write_text("# Title\n\n## Section\n")
        assert _is_placeholder(f)

    def test_only_comments(self, tmp_path: Path) -> None:
        f = tmp_path / "comments.md"
        f.write_text("# Title\n\n<!-- placeholder -->\n")
        assert _is_placeholder(f)

    def test_has_content(self, tmp_path: Path) -> None:
        f = tmp_path / "filled.md"
        f.write_text("# Title\n\nSome actual content here.\n")
        assert not _is_placeholder(f)

    def test_codex_reviewer_line_is_placeholder(self, tmp_path: Path) -> None:
        f = tmp_path / "review.md"
        f.write_text("# Codex Review\n\n## Reviewer\nCodex\n\n## Summary\n<!-- todo -->\n")
        assert _is_placeholder(f)

    def test_none_findings_is_placeholder(self, tmp_path: Path) -> None:
        f = tmp_path / "review.md"
        f.write_text("# Review\n\n### High\n- (none)\n\n### Low\n- (none)\n")
        assert _is_placeholder(f)


class TestCheckCycle:
    def test_fresh_cycle_all_placeholder(self, cycle_dir: Path) -> None:
        result = check_cycle(cycle_dir)
        assert result["phase"] == "started"
        # request has content (version/title), rest are placeholder
        assert len(result["placeholder"]) >= 3
        assert not result["can_finalize"]

    def test_filled_cycle_can_finalize(self, cycle_dir: Path) -> None:
        (cycle_dir / "claude-implementation-summary.md").write_text("# Summary\n\nDid stuff.\n")
        (cycle_dir / "codex-review.md").write_text("# Review\n\nLooks good.\n")
        (cycle_dir / "codex-followup.md").write_text("# Followup\n\nAll accepted.\n")
        (cycle_dir / "final-summary.md").write_text(
            "# Final Summary\n\n## Overview\nDone.\n\n## Changes\n- foo.py\n"
        )
        result = check_cycle(cycle_dir)
        assert result["can_finalize"]
        assert not result["all_issues"]

    def test_missing_overview_section(self, cycle_dir: Path) -> None:
        (cycle_dir / "claude-implementation-summary.md").write_text("# S\n\nDone.\n")
        (cycle_dir / "codex-review.md").write_text("# R\n\nOK.\n")
        (cycle_dir / "codex-followup.md").write_text("# F\n\nOK.\n")
        (cycle_dir / "final-summary.md").write_text("# Final\n\nContent without sections.\n")
        result = check_cycle(cycle_dir)
        assert any("missing overview" in w.lower() for w in result["section_warnings"])


class TestFinalizeCycle:
    def _fill_cycle(self, cycle_dir: Path) -> None:
        (cycle_dir / "claude-implementation-summary.md").write_text("# S\n\nDone.\n")
        (cycle_dir / "codex-review.md").write_text("# R\n\nOK.\n")
        (cycle_dir / "codex-followup.md").write_text("# F\n\nOK.\n")
        (cycle_dir / "final-summary.md").write_text(
            "# Final\n\n## Overview\nDone.\n\n## Changes\n- x\n"
        )

    def test_finalize_normal(self, cfg: Config, cycle_dir: Path) -> None:
        warnings = finalize_cycle(cfg, cycle_dir)
        meta = _read_meta(cycle_dir)
        assert meta["phase"] == "completed"
        assert meta["status"] == "completed"
        assert meta["finished_at"] is not None
        assert len(warnings) > 0  # unfilled files

    def test_finalize_strict_fails(self, cfg: Config, cycle_dir: Path) -> None:
        with pytest.raises(StrictFinalizeError) as exc_info:
            finalize_cycle(cfg, cycle_dir, strict=True)
        assert len(exc_info.value.warnings) > 0

    def test_finalize_strict_passes(self, cfg: Config, cycle_dir: Path) -> None:
        self._fill_cycle(cycle_dir)
        warnings = finalize_cycle(cfg, cycle_dir, strict=True)
        assert warnings == []
        meta = _read_meta(cycle_dir)
        assert meta["phase"] == "completed"

    def test_index_updated(self, cfg: Config, cycle_dir: Path) -> None:
        finalize_cycle(cfg, cycle_dir)
        index = cfg.cycle_root_path / "index.jsonl"
        assert index.exists()
        entries = [json.loads(l) for l in index.read_text().splitlines() if l.strip()]
        assert len(entries) >= 1
        assert entries[-1]["phase"] == "completed"

    def test_version_history_updated(self, cfg: Config, cycle_dir: Path) -> None:
        finalize_cycle(cfg, cycle_dir)
        history = cfg.version_history_path.read_text()
        assert "v0.1.0" in history


class TestNextStep:
    def test_started_phase(self, cycle_dir: Path) -> None:
        ns = next_step(cycle_dir)
        assert ns["phase"] == "started"
        assert "prepare" in ns["command"]
        assert ns["findings_total"] == 0

    def test_review_done_phase(self, cycle_dir: Path) -> None:
        meta = _read_meta(cycle_dir)
        _update_phase(meta, "review_done")
        _write_meta(cycle_dir, meta)
        ns = next_step(cycle_dir)
        assert ns["phase"] == "review_done"
        assert "followup" in ns["command"]
        assert "check" in ns["then"]

    def test_followup_done_phase(self, cycle_dir: Path) -> None:
        meta = _read_meta(cycle_dir)
        _update_phase(meta, "followup_done")
        _write_meta(cycle_dir, meta)
        ns = next_step(cycle_dir)
        assert "check" in ns["command"]
        assert "finalize" in ns["then"]

    def test_strict_ready_when_all_filled(self, cycle_dir: Path) -> None:
        for f in ["claude-implementation-summary.md", "codex-review.md",
                   "codex-followup.md"]:
            (cycle_dir / f).write_text(f"# {f}\n\nContent.\n")
        (cycle_dir / "final-summary.md").write_text(
            "# Final\n\n## Overview\nDone.\n\n## Changes\n- x\n"
        )
        ns = next_step(cycle_dir)
        assert ns["strict_ready"]


class TestDetectRereviewHint:
    def test_no_followup(self, cycle_dir: Path) -> None:
        assert _detect_rereview_hint(cycle_dir) == "unknown"

    def test_high_accepted(self, cycle_dir: Path) -> None:
        (cycle_dir / "codex-followup.md").write_text(
            "# Followup\n\n## Accepted\n- [HIGH] Fixed bug: done\n\n## Deferred\n"
        )
        assert _detect_rereview_hint(cycle_dir) == "recommended"

    def test_medium_only(self, cycle_dir: Path) -> None:
        (cycle_dir / "codex-followup.md").write_text(
            "# Followup\n\n## Accepted\n- [MEDIUM] Improved: done\n\n## Deferred\n"
        )
        assert _detect_rereview_hint(cycle_dir) == "optional"

    def test_low_only(self, cycle_dir: Path) -> None:
        (cycle_dir / "codex-followup.md").write_text(
            "# Followup\n\n## Accepted\n- [LOW] Typo: fixed\n\n## Deferred\n"
        )
        assert _detect_rereview_hint(cycle_dir) == "not_needed"


class TestFindLatestCycle:
    def test_no_cycles(self, cfg: Config) -> None:
        assert find_latest_cycle(cfg) is None

    def test_finds_latest(self, cfg: Config) -> None:
        start_cycle(cfg, "v0.1.0", "first")
        second = start_cycle(cfg, "v0.1.0", "second")
        assert find_latest_cycle(cfg) == second


class TestResolveCycleDir:
    def test_explicit_path(self, cfg: Config, cycle_dir: Path) -> None:
        resolved = _resolve_cycle_dir(cfg, str(cycle_dir))
        assert resolved == cycle_dir

    def test_relative_path(self, cfg: Config, cycle_dir: Path) -> None:
        rel = str(cycle_dir.relative_to(cfg.project_root))
        resolved = _resolve_cycle_dir(cfg, rel)
        assert resolved == cycle_dir

    def test_falls_back_to_latest(self, cfg: Config, cycle_dir: Path) -> None:
        resolved = _resolve_cycle_dir(cfg, None)
        assert resolved == cycle_dir

    def test_raises_when_no_cycles(self, cfg: Config) -> None:
        with pytest.raises(NoCyclesError):
            _resolve_cycle_dir(cfg, None)
