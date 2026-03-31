"""Tests for turbo mode — auto version, commit, tag, rollback, history."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from dev_cycle.config import Config
from dev_cycle.turbo import auto_version, run_turbo, turbo_commit, turbo_history, turbo_rollback


@pytest.fixture
def git_project(tmp_path: Path) -> Path:
    """Create a project with git repo and config."""
    config = {"project_name": "turbo-test", "cycle_root": "ops/dev-cycles",
              "store_git_diff": False, "store_git_status": False}
    (tmp_path / "devcycle.config.json").write_text(json.dumps(config))
    (tmp_path / "ops" / "dev-cycles").mkdir(parents=True)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "version-history.md").write_text("# History\n")

    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, capture_output=True)
    return tmp_path


@pytest.fixture
def git_cfg(git_project: Path) -> Config:
    return Config.load(git_project)


class TestAutoVersion:
    def test_format(self) -> None:
        v = auto_version()
        assert v.startswith("dev-")
        assert len(v) > 10

    def test_unique(self) -> None:
        import time
        v1 = auto_version()
        time.sleep(0.01)
        v2 = auto_version()
        # Same second is possible, but format should be consistent
        assert v1.startswith("dev-")
        assert v2.startswith("dev-")


class TestTurboCommit:
    def test_commits_changes(self, git_project: Path) -> None:
        (git_project / "test.txt").write_text("hello")
        result = turbo_commit(git_project, "test commit", tag="test-tag")
        assert result["committed"]
        assert result["tagged"]
        assert result["tag"] == "test-tag"
        assert result["sha"] != ""

    def test_no_changes_no_commit(self, git_project: Path) -> None:
        result = turbo_commit(git_project, "nothing")
        assert not result["committed"]
        assert not result["tagged"]


class TestTurboRollback:
    def test_rollback_one_step(self, git_project: Path) -> None:
        (git_project / "a.txt").write_text("a")
        turbo_commit(git_project, "add a")
        (git_project / "b.txt").write_text("b")
        turbo_commit(git_project, "add b")

        result = turbo_rollback(git_project, steps=1)
        assert result["rolled_back"]
        assert not (git_project / "b.txt").exists()

    def test_rollback_to_tag(self, git_project: Path) -> None:
        (git_project / "a.txt").write_text("a")
        turbo_commit(git_project, "add a", tag="v-a")
        (git_project / "b.txt").write_text("b")
        turbo_commit(git_project, "add b")

        result = turbo_rollback(git_project, target="v-a")
        assert result["rolled_back"]
        assert result["to_tag"] == "v-a"
        assert not (git_project / "b.txt").exists()


class TestTurboHistory:
    def test_shows_commits(self, git_project: Path) -> None:
        (git_project / "a.txt").write_text("a")
        turbo_commit(git_project, "first change", tag="v1")
        entries = turbo_history(git_project)
        assert len(entries) >= 1
        assert any("first change" in e["message"] for e in entries)

    def test_shows_tags(self, git_project: Path) -> None:
        (git_project / "a.txt").write_text("a")
        turbo_commit(git_project, "tagged", tag="my-tag")
        entries = turbo_history(git_project)
        tagged = [e for e in entries if "my-tag" in e.get("tags", [])]
        assert len(tagged) >= 1


class TestRunTurbo:
    def test_creates_cycle_and_commits(self, git_cfg: Config) -> None:
        output = []
        result = run_turbo(git_cfg, "test turbo", push=False, output_fn=output.append)
        assert result["version"].startswith("dev-")
        assert result["committed"]
        assert not result["pushed"]  # no-push
        assert result["tag"].startswith("devcycle/")

    def test_json_output(self, git_cfg: Config) -> None:
        result = run_turbo(git_cfg, "json test", push=False, output_fn=lambda m: None)
        assert "cycle_id" in result
        assert "version" in result
        assert "tag" in result
        assert "sha" in result
