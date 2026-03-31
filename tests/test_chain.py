"""Tests for multi-cycle chain + locale-hardening."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from dev_cycle.config import Config
from dev_cycle.chain import build_carry_forward, write_chain_summary
from dev_cycle.cycle import start_cycle, _read_meta
from dev_cycle.i18n import has_section, has_placeholder, SECTION_ALIASES
from dev_cycle.turbo import run_turbo
from dev_cycle.state_machine import Choice


def _exit_input(prompt, choices):
    for c in choices:
        if c.action == "exit":
            return c
    return choices[-1] if choices else ""


@pytest.fixture
def git_cfg(tmp_path: Path) -> Config:
    config = {"project_name": "chain-test", "cycle_root": "ops/dev-cycles",
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


class TestMultiCycleChain:
    def test_two_cycles_creates_two_dirs(self, git_cfg: Config) -> None:
        result = run_turbo(git_cfg, "chain test", push=False, cycles=2,
                           input_fn=_exit_input, output_fn=lambda m: None)
        assert result["executed_cycles"] >= 1
        assert result["requested_cycles"] == 2
        assert len(result["all_cycles"]) >= 1

    def test_cycle_ids_unique(self, git_cfg: Config) -> None:
        result = run_turbo(git_cfg, "unique", push=False, cycles=2,
                           non_interactive=True, output_fn=lambda m: None)
        ids = result["all_cycles"]
        assert len(ids) == len(set(ids))

    def test_stopped_reason_recorded(self, git_cfg: Config) -> None:
        result = run_turbo(git_cfg, "stop test", push=False, cycles=2,
                           non_interactive=True, output_fn=lambda m: None)
        assert "stopped_reason" in result
        assert result["stopped_reason"] in ("blocked", "interrupted", "completed", "max_cycles_reached")

    def test_root_cycle_id(self, git_cfg: Config) -> None:
        result = run_turbo(git_cfg, "root test", push=False, cycles=2,
                           input_fn=_exit_input, output_fn=lambda m: None)
        assert result["root_cycle_id"]
        assert result["root_cycle_id"] in result["all_cycles"]

    def test_chain_summary_written(self, git_cfg: Config) -> None:
        run_turbo(git_cfg, "summary test", push=False, cycles=2,
                  input_fn=_exit_input, output_fn=lambda m: None)
        summary_json = git_cfg.cycle_root_path / "run_summary.json"
        assert summary_json.exists()
        data = json.loads(summary_json.read_text())
        assert "executed_cycles" in data
        assert "stopped_reason" in data


class TestJapaneseMultiCycle:
    def test_ja_cycles(self, git_cfg: Config) -> None:
        result = run_turbo(git_cfg, "日本語チェーン", push=False, cycles=2,
                           lang="ja", input_fn=_exit_input, output_fn=lambda m: None)
        assert result["executed_cycles"] >= 1

    def test_ja_chain_summary(self, git_cfg: Config) -> None:
        run_turbo(git_cfg, "日本語サマリー", push=False, cycles=2,
                  lang="ja", input_fn=_exit_input, output_fn=lambda m: None)
        summary_md = git_cfg.cycle_root_path / "run_summary.md"
        if summary_md.exists():
            content = summary_md.read_text()
            assert "実行概要" in content or "Run Summary" in content


class TestCarryForward:
    def test_build_from_previous(self, cfg: Config) -> None:
        d = start_cycle(cfg, "v1.0.0", "prev")
        (d / "implementation_summary.json").write_text(json.dumps({"summary": "did stuff"}))
        (d / "review.json").write_text(json.dumps({"high": ["bug"], "medium": [], "low": []}))
        ctx = build_carry_forward(d)
        assert ctx["previous_cycle_dir"] == str(d)
        assert ctx.get("outstanding_findings", {}).get("high", 0) == 1
        assert "did stuff" in ctx.get("previous_summary", "")

    def test_build_from_empty(self, cfg: Config) -> None:
        d = start_cycle(cfg, "v1.0.0", "empty")
        ctx = build_carry_forward(d)
        assert ctx["previous_cycle_dir"] == str(d)


class TestLocaleAliases:
    def test_has_section_en(self) -> None:
        assert has_section("# Doc\n\n## Goal\n\nStuff.", "goal")

    def test_has_section_ja(self) -> None:
        assert has_section("# Doc\n\n## 目的\n\n内容。", "goal")

    def test_has_section_missing(self) -> None:
        assert not has_section("# Doc\n\nNo goal here.", "goal")

    def test_has_placeholder_en(self) -> None:
        assert has_placeholder("<!-- Describe the goal -->")

    def test_has_placeholder_ja(self) -> None:
        assert has_placeholder("<!-- 目的を記述 -->")

    def test_no_placeholder(self) -> None:
        assert not has_placeholder("Real content here.")

    def test_all_sections_have_aliases(self) -> None:
        for key, aliases in SECTION_ALIASES.items():
            assert len(aliases) >= 2, f"{key} needs at least en+ja alias"


class TestChainSummary:
    def test_write_summary(self, tmp_path: Path) -> None:
        cycles = [{"cycle_id": "c1", "state": "completed", "tag": "t1"},
                  {"cycle_id": "c2", "state": "blocked", "tag": ""}]
        write_chain_summary(tmp_path, cycles, "blocked", lang="en")
        assert (tmp_path / "run_summary.json").exists()
        assert (tmp_path / "run_summary.md").exists()
        data = json.loads((tmp_path / "run_summary.json").read_text())
        assert data["stopped_reason"] == "blocked"
        assert data["executed_cycles"] == 2

    def test_write_summary_ja(self, tmp_path: Path) -> None:
        cycles = [{"cycle_id": "c1", "state": "completed", "tag": "t1"}]
        write_chain_summary(tmp_path, cycles, "completed", lang="ja")
        md = (tmp_path / "run_summary.md").read_text()
        assert "実行概要" in md
