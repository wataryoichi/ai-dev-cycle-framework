"""Tests for Claude runner integration into orchestrator."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dev_cycle.config import Config
from dev_cycle.cycle import _read_meta, start_cycle
from dev_cycle.orchestrator import RunResult, _drive, resume_cycle
from dev_cycle.state_machine import Choice, State, determine_state


def _exit_input(prompt, choices):
    """Always exit at decision points."""
    for c in choices:
        if c.action == "exit":
            return c
    return choices[-1] if choices else ""


class TestClaudeRunnerInOrchestrator:
    def test_claude_configured_auto_advances(self, cfg: Config, monkeypatch) -> None:
        """When DEVCYCLE_CLAUDE_CMD is set and impl is filled, should advance."""
        monkeypatch.setenv("DEVCYCLE_CLAUDE_CMD", "echo 'implemented feature X'")
        cycle_dir = start_cycle(cfg, "v1.0.0", "claude test")
        # Fill request so state is IMPLEMENTING
        (cycle_dir / "request.md").write_text("# Request\n\n## Goal\nBuild X.\n")

        output = []
        result = _drive(cfg, cycle_dir, _exit_input, output.append, non_interactive=False)

        # Claude runner should have been called and written summary
        summary = (cycle_dir / "claude-implementation-summary.md").read_text()
        assert "implemented" in summary.lower() or len(summary) > 50
        assert any("Claude" in o for o in output)

    def test_claude_not_configured_falls_through(self, cfg: Config, monkeypatch) -> None:
        """When DEVCYCLE_CLAUDE_CMD is not set, falls to interactive/non-interactive."""
        monkeypatch.delenv("DEVCYCLE_CLAUDE_CMD", raising=False)
        cycle_dir = start_cycle(cfg, "v1.0.0", "no claude")
        (cycle_dir / "request.md").write_text("# Request\n\n## Goal\nBuild Y.\n")

        result = _drive(cfg, cycle_dir, _exit_input, lambda m: None, non_interactive=True)

        # Should block because Claude can't run and non-interactive defaults to exit
        assert result.interrupted

    def test_claude_failure_doesnt_crash(self, cfg: Config, monkeypatch) -> None:
        """Command failure should not crash, just fall through."""
        monkeypatch.setenv("DEVCYCLE_CLAUDE_CMD", "false")  # exit code 1
        cycle_dir = start_cycle(cfg, "v1.0.0", "fail test")
        (cycle_dir / "request.md").write_text("# Request\n\n## Goal\nTest.\n")

        output = []
        result = _drive(cfg, cycle_dir, _exit_input, output.append, non_interactive=True)

        # Should not crash, just block
        assert result.interrupted


class TestDualJsonOnCreate:
    def test_request_json_created(self, cfg: Config) -> None:
        cycle_dir = start_cycle(cfg, "v1.0.0", "dual test")
        assert (cycle_dir / "request.json").exists()
        data = json.loads((cycle_dir / "request.json").read_text())
        assert data["title"] == "dual test"
        assert data["version"] == "v1.0.0"

    def test_cycle_state_json_created(self, cfg: Config) -> None:
        cycle_dir = start_cycle(cfg, "v1.0.0", "state test")
        assert (cycle_dir / "cycle_state.json").exists()
        data = json.loads((cycle_dir / "cycle_state.json").read_text())
        assert data["state"] == "started"
        assert data["cycle_id"]

    def test_meta_json_still_works(self, cfg: Config) -> None:
        cycle_dir = start_cycle(cfg, "v1.0.0", "meta test")
        meta = _read_meta(cycle_dir)
        assert meta["phase"] == "started"
        assert meta["title"] == "meta test"

    def test_request_md_and_json_consistent(self, cfg: Config) -> None:
        cycle_dir = start_cycle(cfg, "v1.0.0", "consistency")
        md = (cycle_dir / "request.md").read_text()
        data = json.loads((cycle_dir / "request.json").read_text())
        assert "consistency" in md
        assert data["title"] == "consistency"
