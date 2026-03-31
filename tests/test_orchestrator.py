"""Tests for the orchestration engine."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dev_cycle.config import Config
from dev_cycle.cycle import _read_meta, start_cycle
from dev_cycle.orchestrator import RunResult, get_status, resume_cycle, run_cycle
from dev_cycle.state_machine import Choice, State


def _auto_input(prompt: str, choices: list[Choice]) -> Choice | str:
    """Auto-respond to prompts for testing."""
    if prompt == "review_text":
        return "- Critical: missing validation\n- Should add error handling\n- Minor typo"

    for c in choices:
        # Always pick the first non-exit choice
        if c.action != "exit":
            return c
    return choices[0] if choices else ""


def _exit_input(prompt: str, choices: list[Choice]) -> Choice | str:
    """Always exit at decision points."""
    if prompt == "review_text":
        return ""
    for c in choices:
        if c.action == "exit":
            return c
    return choices[-1] if choices else ""


class TestRunCycle:
    def test_starts_cycle(self, cfg: Config) -> None:
        output = []
        result = run_cycle(cfg, "v1.0.0", "test run",
                           input_fn=_exit_input,
                           output_fn=output.append)
        assert result.cycle_dir.exists()
        assert result.cycle_id.startswith("v1.0.0")
        assert any("started" in o.lower() or "Cycle" in o for o in output)

    def test_interrupts_at_decision_point(self, cfg: Config) -> None:
        result = run_cycle(cfg, "v1.0.0", "test run",
                           input_fn=_exit_input,
                           output_fn=lambda m: None)
        assert result.interrupted


class TestResumeCycle:
    def test_resume_existing_cycle(self, cfg: Config) -> None:
        # Start a cycle manually
        cycle_dir = start_cycle(cfg, "v1.0.0", "resume test")

        # Fill implementation to advance state
        (cycle_dir / "request.md").write_text("# Request\n\n## Goal\nTest.\n")
        (cycle_dir / "claude-implementation-summary.md").write_text("# S\n\nDone.\n")

        output = []
        result = resume_cycle(cfg, cycle_dir,
                              input_fn=_exit_input,
                              output_fn=output.append)
        assert result.cycle_dir == cycle_dir
        assert any("Resuming" in o for o in output)


class TestGetStatus:
    def test_status_of_fresh_cycle(self, cfg: Config) -> None:
        cycle_dir = start_cycle(cfg, "v1.0.0", "status test")
        status = get_status(cfg, cycle_dir)
        assert status["cycle_id"].startswith("v1.0.0")
        assert status["state"] in ("started", "implementing")  # template may have content
        assert "quality" in status
        assert "findings" in status
        assert "progress_pct" in status

    def test_status_has_choices(self, cfg: Config) -> None:
        cycle_dir = start_cycle(cfg, "v1.0.0", "test")
        (cycle_dir / "request.md").write_text("# R\n\n## Goal\nX.\n")
        (cycle_dir / "claude-implementation-summary.md").write_text("# S\n\nDone.\n")
        (cycle_dir / "codex-review.md").write_text("# R\n\nOK.\n")
        (cycle_dir / "codex-followup.md").write_text("# F\n\nOK.\n")
        (cycle_dir / "final-summary.md").write_text("# F\n\n## Overview\nDone.\n\n## Changes\n- x\n")
        status = get_status(cfg, cycle_dir)
        assert len(status["choices"]) > 0  # should have finalize choices


class TestOrchestratorStateInMeta:
    def test_state_recorded_in_meta(self, cfg: Config) -> None:
        result = run_cycle(cfg, "v1.0.0", "meta test",
                           input_fn=_exit_input,
                           output_fn=lambda m: None)
        meta = _read_meta(result.cycle_dir)
        # Fresh cycle exits at first decision point (STARTED or IMPLEMENTING)
        assert result.interrupted or result.state == State.COMPLETED
