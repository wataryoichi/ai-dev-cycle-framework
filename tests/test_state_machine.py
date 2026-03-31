"""Tests for the state machine."""

from __future__ import annotations

from pathlib import Path

import pytest

from dev_cycle.config import Config
from dev_cycle.cycle import _read_meta, _update_phase, _write_meta, start_cycle
from dev_cycle.review_importer import import_review
from dev_cycle.state_machine import (
    State,
    STATE_TO_PHASE,
    determine_state,
    get_auto_transition,
    get_choices,
    get_transitions,
)


class TestDetermineState:
    def test_fresh_cycle_is_started(self, cfg: Config) -> None:
        d = start_cycle(cfg, "v1.0.0", "test")
        assert determine_state(d) == State.STARTED

    def test_with_filled_request_is_implementing(self, cfg: Config) -> None:
        d = start_cycle(cfg, "v1.0.0", "test")
        (d / "request.md").write_text("# Request\n\n## Goal\nDo something.\n")
        assert determine_state(d) == State.IMPLEMENTING

    def test_with_impl_is_review_needed(self, cfg: Config) -> None:
        d = start_cycle(cfg, "v1.0.0", "test")
        (d / "claude-implementation-summary.md").write_text("# Summary\n\nDid stuff.\n")
        assert determine_state(d) == State.REVIEW_NEEDED

    def test_review_pending(self, cfg: Config) -> None:
        d = start_cycle(cfg, "v1.0.0", "test")
        meta = _read_meta(d)
        _update_phase(meta, "review_pending")
        _write_meta(d, meta)
        assert determine_state(d) == State.REVIEW_PENDING

    def test_review_imported(self, cfg: Config) -> None:
        d = start_cycle(cfg, "v1.0.0", "test")
        import_review(d, "- Critical: missing validation\n- Should add tests")
        assert determine_state(d) == State.FOLLOWUP_NEEDED

    def test_followup_filled_is_fix_needed(self, cfg: Config) -> None:
        d = start_cycle(cfg, "v1.0.0", "test")
        import_review(d, "- Bug found")
        (d / "codex-followup.md").write_text("# Followup\n\n## Accepted\n- Bug: fixed\n")
        assert determine_state(d) == State.FIX_NEEDED

    def test_all_filled_is_ready_to_finalize(self, cfg: Config) -> None:
        d = start_cycle(cfg, "v1.0.0", "test")
        (d / "claude-implementation-summary.md").write_text("# S\n\nDone.\n")
        (d / "codex-review.md").write_text("# R\n\nOK.\n")
        (d / "codex-followup.md").write_text("# F\n\nOK.\n")
        (d / "final-summary.md").write_text("# Final\n\n## Overview\nDone.\n\n## Changes\n- x\n")
        assert determine_state(d) == State.READY_TO_FINALIZE

    def test_completed(self, cfg: Config) -> None:
        d = start_cycle(cfg, "v1.0.0", "test")
        meta = _read_meta(d)
        _update_phase(meta, "completed")
        _write_meta(d, meta)
        assert determine_state(d) == State.COMPLETED


class TestTransitions:
    def test_started_has_transition(self) -> None:
        ts = get_transitions(State.STARTED)
        assert len(ts) >= 1

    def test_review_needed_is_auto(self) -> None:
        auto = get_auto_transition(State.REVIEW_NEEDED)
        assert auto is not None
        assert auto.auto

    def test_implementing_has_choices(self) -> None:
        choices = get_choices(State.IMPLEMENTING)
        assert len(choices) >= 2

    def test_review_pending_needs_input(self) -> None:
        ts = get_transitions(State.REVIEW_PENDING)
        assert any(t.needs_input == "review_text" for t in ts)

    def test_ready_to_finalize_has_choices(self) -> None:
        choices = get_choices(State.READY_TO_FINALIZE)
        assert any(c.action == "finalize_strict" for c in choices)
        assert any(c.action == "finalize" for c in choices)

    def test_completed_has_no_transitions(self) -> None:
        ts = get_transitions(State.COMPLETED)
        assert ts == []


class TestStateToPhase:
    def test_all_states_mapped(self) -> None:
        for state in State:
            assert state in STATE_TO_PHASE, f"{state} not in STATE_TO_PHASE"
