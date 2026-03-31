"""CLI-level tests — invoke commands and check stdout/stderr/exit code."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)


def run_cli(*args: str, cwd: Path, stdin: str | None = None) -> subprocess.CompletedProcess:
    """Run a CLI command and return the result."""
    import os
    env = os.environ.copy()
    env["PYTHONPATH"] = PROJECT_ROOT
    cmd = [sys.executable, "-m", "dev_cycle.cli", "--project-root", str(cwd), *args]
    return subprocess.run(
        cmd, capture_output=True, text=True, cwd=PROJECT_ROOT,
        input=stdin, timeout=30, env=env,
    )


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """Create a project with config."""
    config = {
        "project_name": "cli-test",
        "cycle_root": "ops/dev-cycles",
        "version_history_file": "docs/version-history.md",
        "store_git_diff": False,
        "store_git_status": False,
    }
    (tmp_path / "devcycle.config.json").write_text(json.dumps(config))
    (tmp_path / "ops" / "dev-cycles").mkdir(parents=True)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "version-history.md").write_text("# Version History\n")
    return tmp_path


class TestStartCycleCLI:
    def test_normal_output(self, project: Path) -> None:
        r = run_cli("start-cycle", "--version", "v1.0.0", "--title", "test", cwd=project)
        assert r.returncode == 0
        assert "Cycle started:" in r.stdout

    def test_json_output(self, project: Path) -> None:
        r = run_cli("start-cycle", "--version", "v1.0.0", "--title", "test", "--json", cwd=project)
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["version"] == "v1.0.0"
        assert data["title"] == "test"
        assert data["phase"] == "started"
        assert "cycle_dir" in data


class TestNextStepCLI:
    def test_normal_output(self, project: Path) -> None:
        run_cli("start-cycle", "--version", "v1.0.0", "--title", "t", cwd=project)
        r = run_cli("next-step", cwd=project)
        assert r.returncode == 0
        assert "Phase:" in r.stdout
        assert "Next:" in r.stdout

    def test_json_output(self, project: Path) -> None:
        run_cli("start-cycle", "--version", "v1.0.0", "--title", "t", cwd=project)
        r = run_cli("next-step", "--json", cwd=project)
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["phase"] == "started"
        assert "command" in data
        assert "strict_ready" in data
        assert "rereview_hint" in data

    def test_no_cycles(self, project: Path) -> None:
        r = run_cli("next-step", cwd=project)
        assert r.returncode != 0


class TestCheckCycleCLI:
    def test_fresh_cycle_has_issues(self, project: Path) -> None:
        run_cli("start-cycle", "--version", "v1.0.0", "--title", "t", cwd=project)
        r = run_cli("check-cycle", cwd=project)
        assert r.returncode == 1  # issues found

    def test_json_output(self, project: Path) -> None:
        run_cli("start-cycle", "--version", "v1.0.0", "--title", "t", cwd=project)
        r = run_cli("check-cycle", "--json", cwd=project)
        data = json.loads(r.stdout)
        assert "strict_ready" in data
        assert data["strict_ready"] is False
        assert "findings" in data


class TestImportReviewCLI:
    def test_from_text(self, project: Path) -> None:
        run_cli("start-cycle", "--version", "v1.0.0", "--title", "t", cwd=project)
        r = run_cli("import-review", "--text", "- Critical: bug found", cwd=project)
        assert r.returncode == 0
        assert "Review imported" in r.stdout

    def test_from_stdin(self, project: Path) -> None:
        run_cli("start-cycle", "--version", "v1.0.0", "--title", "t", cwd=project)
        r = run_cli("import-review", cwd=project, stdin="- Should fix this")
        assert r.returncode == 0

    def test_json_output(self, project: Path) -> None:
        run_cli("start-cycle", "--version", "v1.0.0", "--title", "t", cwd=project)
        r = run_cli("import-review", "--text", "- Bug", "--json", cwd=project)
        data = json.loads(r.stdout)
        assert data["phase"] == "review_imported"
        assert "findings" in data

    def test_empty_stdin_error(self, project: Path) -> None:
        run_cli("start-cycle", "--version", "v1.0.0", "--title", "t", cwd=project)
        r = run_cli("import-review", cwd=project, stdin="")
        assert r.returncode != 0
        assert "empty" in r.stderr.lower() or "Error" in r.stderr


class TestRunReviewLoopCLI:
    def test_with_text(self, project: Path) -> None:
        run_cli("start-cycle", "--version", "v1.0.0", "--title", "t", cwd=project)
        r = run_cli("run-review-loop", "--text", "- Bug found", "--generate-followup", cwd=project)
        assert r.returncode == 0
        assert "Review loop complete" in r.stdout or "Findings" in r.stdout

    def test_json_output(self, project: Path) -> None:
        run_cli("start-cycle", "--version", "v1.0.0", "--title", "t", cwd=project)
        r = run_cli("run-review-loop", "--text", "- Bug found", "--json", cwd=project)
        data = json.loads(r.stdout)
        assert "findings" in data
        assert "next_command" in data
        assert "strict_ready" in data


class TestFinalizeCycleCLI:
    def test_normal_with_warnings(self, project: Path) -> None:
        run_cli("start-cycle", "--version", "v1.0.0", "--title", "t", cwd=project)
        r = run_cli("finalize-cycle", cwd=project)
        assert r.returncode == 0
        assert "finalized" in r.stdout.lower()

    def test_strict_fails_on_empty(self, project: Path) -> None:
        run_cli("start-cycle", "--version", "v1.0.0", "--title", "t", cwd=project)
        r = run_cli("finalize-cycle", "--strict", cwd=project)
        assert r.returncode != 0
        assert "strict" in r.stderr.lower() or "refusing" in r.stderr.lower()

    def test_json_output(self, project: Path) -> None:
        run_cli("start-cycle", "--version", "v1.0.0", "--title", "t", cwd=project)
        r = run_cli("finalize-cycle", "--json", cwd=project)
        data = json.loads(r.stdout)
        assert data["phase"] == "completed"
        assert "warnings" in data


class TestGenerateFollowupCLI:
    def test_after_review(self, project: Path) -> None:
        run_cli("start-cycle", "--version", "v1.0.0", "--title", "t", cwd=project)
        run_cli("import-review", "--text", "- Critical: bug", cwd=project)
        r = run_cli("generate-followup", cwd=project)
        assert r.returncode == 0
        assert "Follow-up draft" in r.stdout

    def test_json_output(self, project: Path) -> None:
        run_cli("start-cycle", "--version", "v1.0.0", "--title", "t", cwd=project)
        run_cli("import-review", "--text", "- Critical: bug", cwd=project)
        r = run_cli("generate-followup", "--json", cwd=project)
        data = json.loads(r.stdout)
        assert "findings" in data


class TestPrepareReviewCLI:
    def test_json_output(self, project: Path) -> None:
        run_cli("start-cycle", "--version", "v1.0.0", "--title", "my feature", cwd=project)
        r = run_cli("prepare-review", "--json", cwd=project)
        data = json.loads(r.stdout)
        assert data["title"] == "my feature"
        assert "prompt" in data
        assert "import_command" in data


class TestShortAliases:
    """Test that short alias names work."""

    def test_start(self, project: Path) -> None:
        r = run_cli("start", "--version", "v1.0.0", "--title", "alias test", cwd=project)
        assert r.returncode == 0
        assert "Cycle started" in r.stdout

    def test_next(self, project: Path) -> None:
        run_cli("start", "--version", "v1.0.0", "--title", "t", cwd=project)
        r = run_cli("next", cwd=project)
        assert r.returncode == 0
        assert "Phase:" in r.stdout

    def test_check(self, project: Path) -> None:
        run_cli("start", "--version", "v1.0.0", "--title", "t", cwd=project)
        r = run_cli("check", cwd=project)
        assert "Quality:" in r.stdout

    def test_finalize(self, project: Path) -> None:
        run_cli("start", "--version", "v1.0.0", "--title", "t", cwd=project)
        r = run_cli("finalize", cwd=project)
        assert r.returncode == 0
        assert "finalized" in r.stdout.lower()

    def test_followup(self, project: Path) -> None:
        run_cli("start", "--version", "v1.0.0", "--title", "t", cwd=project)
        run_cli("import-review", "--text", "- Bug found", cwd=project)
        r = run_cli("followup", cwd=project)
        assert r.returncode == 0
        assert "Follow-up draft" in r.stdout

    def test_review_loop(self, project: Path) -> None:
        run_cli("start", "--version", "v1.0.0", "--title", "t", cwd=project)
        r = run_cli("review-loop", "--text", "- Bug", cwd=project)
        assert r.returncode == 0

    def test_prepare(self, project: Path) -> None:
        run_cli("start", "--version", "v1.0.0", "--title", "t", cwd=project)
        r = run_cli("prepare", "--json", cwd=project)
        data = json.loads(r.stdout)
        assert "prompt" in data

    def test_index(self, project: Path) -> None:
        r = run_cli("index", "--format", "markdown", cwd=project)
        assert r.returncode == 0


class TestVersion:
    def test_version_flag(self, project: Path) -> None:
        r = run_cli("--version", cwd=project)
        assert r.returncode == 0
        assert "devcycle" in r.stdout
        assert "devcycle" in r.stdout
        # Version number should be present
        assert r.stdout.strip().startswith("devcycle ")
