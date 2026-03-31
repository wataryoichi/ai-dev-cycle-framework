"""Tests for configuration loading."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dev_cycle.config import Config, DEFAULT_CONFIG_NAME


class TestConfigLoad:
    def test_loads_from_file(self, tmp_path: Path) -> None:
        config = {"project_name": "my-proj", "cycle_root": "cycles"}
        (tmp_path / DEFAULT_CONFIG_NAME).write_text(json.dumps(config))
        cfg = Config.load(tmp_path)
        assert cfg.project_name == "my-proj"
        assert cfg.cycle_root == "cycles"
        assert cfg.project_root == tmp_path

    def test_defaults_applied(self, tmp_path: Path) -> None:
        config = {"project_name": "test"}
        (tmp_path / DEFAULT_CONFIG_NAME).write_text(json.dumps(config))
        cfg = Config.load(tmp_path)
        assert cfg.cycle_root == "ops/dev-cycles"
        assert cfg.version_history_file == "docs/version-history.md"
        assert cfg.default_branch == "main"
        assert cfg.reviewers == ["codex"]
        assert cfg.store_git_diff is True
        assert cfg.store_git_status is True

    def test_missing_config_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="devcycle.config.json"):
            Config.load(tmp_path)

    def test_cycle_root_path(self, tmp_path: Path) -> None:
        config = {"project_name": "test", "cycle_root": "my/cycles"}
        (tmp_path / DEFAULT_CONFIG_NAME).write_text(json.dumps(config))
        cfg = Config.load(tmp_path)
        assert cfg.cycle_root_path == tmp_path / "my" / "cycles"

    def test_version_history_path(self, tmp_path: Path) -> None:
        config = {"project_name": "test", "version_history_file": "history.md"}
        (tmp_path / DEFAULT_CONFIG_NAME).write_text(json.dumps(config))
        cfg = Config.load(tmp_path)
        assert cfg.version_history_path == tmp_path / "history.md"

    def test_overrides(self, tmp_path: Path) -> None:
        config = {
            "project_name": "test",
            "store_git_diff": False,
            "store_git_status": False,
            "default_branch": "develop",
            "reviewers": ["alice", "bob"],
        }
        (tmp_path / DEFAULT_CONFIG_NAME).write_text(json.dumps(config))
        cfg = Config.load(tmp_path)
        assert cfg.store_git_diff is False
        assert cfg.store_git_status is False
        assert cfg.default_branch == "develop"
        assert cfg.reviewers == ["alice", "bob"]
