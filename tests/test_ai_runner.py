"""Tests for AI runners (Claude + Codex)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from dev_cycle.ai_runner import (
    get_claude_cmd,
    get_codex_cmd,
    run_claude,
    run_codex,
    _build_impl_prompt,
    _build_review_prompt,
)


@pytest.fixture
def cycle_dir(tmp_path: Path) -> Path:
    d = tmp_path / "cycle"
    d.mkdir()
    (d / "request.md").write_text("# Request\n\n## Goal\nBuild feature.\n")
    return d


class TestGetCommands:
    def test_claude_cmd_from_env(self, monkeypatch) -> None:
        monkeypatch.setenv("DEVCYCLE_CLAUDE_CMD", "echo test")
        assert get_claude_cmd() == "echo test"

    def test_claude_cmd_missing(self, monkeypatch) -> None:
        monkeypatch.delenv("DEVCYCLE_CLAUDE_CMD", raising=False)
        assert get_claude_cmd() == ""

    def test_codex_cmd_from_env(self, monkeypatch) -> None:
        monkeypatch.setenv("DEVCYCLE_CODEX_CMD", "echo review")
        assert get_codex_cmd() == "echo review"

    def test_codex_cmd_missing(self, monkeypatch) -> None:
        monkeypatch.delenv("DEVCYCLE_CODEX_CMD", raising=False)
        assert get_codex_cmd() == ""


class TestRunClaude:
    def test_blocked_when_not_configured(self, monkeypatch, cycle_dir) -> None:
        monkeypatch.delenv("DEVCYCLE_CLAUDE_CMD", raising=False)
        result = run_claude(cycle_dir, "test")
        assert result["blocked"]
        assert not result["success"]
        assert "not set" in result["reason"]

    def test_runs_command(self, monkeypatch, cycle_dir) -> None:
        monkeypatch.setenv("DEVCYCLE_CLAUDE_CMD", "echo implemented")
        result = run_claude(cycle_dir, "test feature")
        assert result["success"]
        assert not result["blocked"]
        assert "implemented" in result["output"]


class TestRunCodex:
    def test_blocked_when_not_configured(self, monkeypatch, cycle_dir) -> None:
        monkeypatch.delenv("DEVCYCLE_CODEX_CMD", raising=False)
        result = run_codex(cycle_dir, "test")
        assert result["blocked"]
        assert not result["success"]

    def test_runs_command(self, monkeypatch, cycle_dir) -> None:
        monkeypatch.setenv("DEVCYCLE_CODEX_CMD", "echo")
        result = run_codex(cycle_dir, "test review")
        assert result["success"]
        assert result["review_text"] != ""


class TestPromptBuilding:
    def test_impl_prompt_includes_title(self, cycle_dir) -> None:
        prompt = _build_impl_prompt(cycle_dir, "my feature", "build it")
        assert "my feature" in prompt
        assert "build it" in prompt

    def test_review_prompt(self) -> None:
        prompt = _build_review_prompt("test changes")
        assert "test changes" in prompt
        assert "High" in prompt
