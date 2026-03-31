"""Tests for i18n and multi-cycle."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dev_cycle.config import Config
from dev_cycle.cycle import start_cycle, _read_meta
from dev_cycle.i18n import get_labels, resolve_lang
from dev_cycle.turbo import run_turbo
from dev_cycle.state_machine import Choice


def _exit_input(prompt, choices):
    for c in choices:
        if c.action == "exit":
            return c
    return choices[-1] if choices else ""


class TestGetLabels:
    def test_english(self) -> None:
        L = get_labels("en")
        assert L["goal"] == "Goal"
        assert L["overview"] == "Overview"

    def test_japanese(self) -> None:
        L = get_labels("ja")
        assert L["goal"] == "目的"
        assert L["overview"] == "概要"

    def test_fallback(self) -> None:
        L = get_labels("xx")
        assert L["goal"] == "Goal"  # falls back to en

    def test_none_fallback(self) -> None:
        L = get_labels(None)
        assert L["goal"] == "Goal"


class TestResolveLang:
    def test_cli_wins(self) -> None:
        assert resolve_lang("ja", "en") == "ja"

    def test_config_fallback(self) -> None:
        assert resolve_lang(None, "ja") == "ja"

    def test_default(self) -> None:
        assert resolve_lang(None, None) == "en"


class TestJapaneseOutput:
    def test_request_md_japanese(self, cfg: Config) -> None:
        d = start_cycle(cfg, "v1.0.0", "テスト", lang="ja")
        md = (d / "request.md").read_text()
        assert "目的" in md
        assert "背景" in md
        assert "スコープ" in md

    def test_request_json_has_lang(self, cfg: Config) -> None:
        d = start_cycle(cfg, "v1.0.0", "テスト", lang="ja")
        data = json.loads((d / "request.json").read_text())
        assert data["lang"] == "ja"
        assert data["title"] == "テスト"

    def test_meta_has_lang(self, cfg: Config) -> None:
        d = start_cycle(cfg, "v1.0.0", "テスト", lang="ja")
        meta = _read_meta(d)
        assert meta["lang"] == "ja"

    def test_english_default(self, cfg: Config) -> None:
        d = start_cycle(cfg, "v1.0.0", "test")
        md = (d / "request.md").read_text()
        assert "Goal" in md
        assert "Context" in md


class TestMultiCycleTurbo:
    def test_two_cycles(self, git_cfg: Config) -> None:
        result = run_turbo(git_cfg, "multi test", push=False, cycles=2,
                           input_fn=_exit_input, output_fn=lambda m: None)
        assert result["executed_cycles"] >= 1
        assert result["requested_cycles"] == 2

    def test_single_cycle_default(self, git_cfg: Config) -> None:
        result = run_turbo(git_cfg, "single test", push=False,
                           input_fn=_exit_input, output_fn=lambda m: None)
        assert result["executed_cycles"] == 1
        assert result["requested_cycles"] == 1

    def test_multi_cycle_ids_unique(self, git_cfg: Config) -> None:
        result = run_turbo(git_cfg, "unique test", push=False, cycles=2,
                           non_interactive=True, output_fn=lambda m: None)
        ids = result.get("all_cycles", [])
        assert len(ids) == len(set(ids))  # all unique

    def test_multi_cycle_japanese(self, git_cfg: Config) -> None:
        result = run_turbo(git_cfg, "日本語テスト", push=False, lang="ja",
                           input_fn=_exit_input, output_fn=lambda m: None)
        assert result["executed_cycles"] >= 1


# Need git_cfg fixture for turbo tests
@pytest.fixture
def git_cfg(tmp_path: Path) -> Config:
    import subprocess
    config = {"project_name": "test", "cycle_root": "ops/dev-cycles",
              "store_git_diff": False, "store_git_status": False}
    (tmp_path / "devcycle.config.json").write_text(json.dumps(config))
    (tmp_path / "ops" / "dev-cycles").mkdir(parents=True)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "version-history.md").write_text("# History\n")
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, capture_output=True)
    return Config.load(tmp_path)
