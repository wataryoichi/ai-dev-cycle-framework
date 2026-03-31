"""Tests for non-interactive mode."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dev_cycle.config import Config
from dev_cycle.cycle import _read_meta, start_cycle
from dev_cycle.orchestrator import RunResult, resume_cycle, run_cycle
from dev_cycle.review_importer import import_review
from dev_cycle.state_machine import State, get_blocking_reason, get_default_action


class TestNonInteractiveRun:
    def test_blocks_at_implementing(self, cfg: Config) -> None:
        result = run_cycle(cfg, "v1.0.0", "ni test",
                           output_fn=lambda m: None,
                           non_interactive=True)
        # Fresh cycle: started → no auto transition → blocks
        assert result.interrupted
        assert result.blocked

    def test_blocked_reason_present(self, cfg: Config) -> None:
        result = run_cycle(cfg, "v1.0.0", "ni test",
                           output_fn=lambda m: None,
                           non_interactive=True)
        assert result.blocked_reason != ""

    def test_output_shows_blocked(self, cfg: Config) -> None:
        msgs = []
        result = run_cycle(cfg, "v1.0.0", "ni test",
                           output_fn=msgs.append,
                           non_interactive=True)
        assert any("Blocked" in m or "blocked" in m.lower() for m in msgs)


class TestNonInteractiveResume:
    def test_resumes_and_auto_advances(self, cfg: Config) -> None:
        # Create cycle with impl filled → should auto-advance to review_pending
        cycle_dir = start_cycle(cfg, "v1.0.0", "resume ni")
        (cycle_dir / "claude-implementation-summary.md").write_text("# S\n\nDone.\n")

        result = resume_cycle(cfg, cycle_dir,
                              output_fn=lambda m: None,
                              non_interactive=True)
        # Should auto-advance through review_needed (auto) then block at review_pending
        assert result.blocked
        assert result.state in (State.REVIEW_PENDING, State.REVIEW_NEEDED)

    def test_blocks_at_review_pending(self, cfg: Config) -> None:
        cycle_dir = start_cycle(cfg, "v1.0.0", "review block")
        (cycle_dir / "claude-implementation-summary.md").write_text("# S\n\nDone.\n")

        result = resume_cycle(cfg, cycle_dir,
                              output_fn=lambda m: None,
                              non_interactive=True)
        assert result.blocked
        assert "review" in result.blocked_reason.lower() or "input" in result.blocked_reason.lower()

    def test_auto_finalize_when_ready(self, cfg: Config) -> None:
        # Fully filled cycle at ready_to_finalize → default is "finalize"
        cycle_dir = start_cycle(cfg, "v1.0.0", "auto fin")
        (cycle_dir / "claude-implementation-summary.md").write_text("# S\n\nDone.\n")
        (cycle_dir / "codex-review.md").write_text("# R\n\nOK.\n")
        (cycle_dir / "codex-followup.md").write_text("# F\n\nOK.\n")
        (cycle_dir / "final-summary.md").write_text("# F\n\n## Overview\nDone.\n\n## Changes\n- x\n")

        result = resume_cycle(cfg, cycle_dir,
                              output_fn=lambda m: None,
                              non_interactive=True)
        meta = _read_meta(cycle_dir)
        assert meta["phase"] == "completed" or result.state == State.COMPLETED


class TestDefaultActions:
    def test_implementing_defaults_to_exit(self) -> None:
        assert get_default_action(State.IMPLEMENTING) == "exit"

    def test_followup_ready_defaults_to_exit(self) -> None:
        assert get_default_action(State.FOLLOWUP_READY) == "exit"

    def test_fix_needed_defaults_to_exit(self) -> None:
        assert get_default_action(State.FIX_NEEDED) == "exit"

    def test_ready_to_finalize_defaults_to_finalize(self) -> None:
        assert get_default_action(State.READY_TO_FINALIZE) == "finalize"

    def test_review_needed_has_auto(self) -> None:
        # No default needed — it's auto
        assert get_default_action(State.REVIEW_NEEDED) == "exit"  # fallback


class TestBlockingReasons:
    def test_review_pending_has_reason(self) -> None:
        reason = get_blocking_reason(State.REVIEW_PENDING)
        assert "review" in reason.lower()

    def test_implementing_has_reason(self) -> None:
        reason = get_blocking_reason(State.IMPLEMENTING)
        assert reason != ""

    def test_ready_to_finalize_no_block(self) -> None:
        reason = get_blocking_reason(State.READY_TO_FINALIZE)
        assert reason == ""
