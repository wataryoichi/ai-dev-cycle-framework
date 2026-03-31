"""Tests for devcycle doctor."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dev_cycle.doctor import run_doctor, format_doctor


@pytest.fixture
def project_with_config(tmp_path: Path) -> Path:
    config = {"project_name": "test", "cycle_root": "ops/dev-cycles"}
    (tmp_path / "devcycle.config.json").write_text(json.dumps(config))
    (tmp_path / "ops" / "dev-cycles").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def bare_project(tmp_path: Path) -> Path:
    return tmp_path


class TestDoctorChecks:
    def test_config_found(self, project_with_config: Path) -> None:
        result = run_doctor(project_with_config)
        names = {c["name"]: c["status"] for c in result["checks"]}
        assert names["config"] == "ok"

    def test_config_missing(self, bare_project: Path) -> None:
        result = run_doctor(bare_project)
        names = {c["name"]: c["status"] for c in result["checks"]}
        assert names["config"] == "error"

    def test_cycle_root_exists(self, project_with_config: Path) -> None:
        result = run_doctor(project_with_config)
        names = {c["name"]: c["status"] for c in result["checks"]}
        assert names["cycle_root"] == "ok"

    def test_cycle_root_missing(self, bare_project: Path) -> None:
        (bare_project / "devcycle.config.json").write_text(
            json.dumps({"project_name": "t", "cycle_root": "missing/dir"})
        )
        result = run_doctor(bare_project)
        names = {c["name"]: c["status"] for c in result["checks"]}
        assert names["cycle_root"] == "error"

    def test_write_access(self, project_with_config: Path) -> None:
        result = run_doctor(project_with_config)
        names = {c["name"]: c["status"] for c in result["checks"]}
        assert names["write_access"] == "ok"

    def test_overall_error_when_config_missing(self, bare_project: Path) -> None:
        result = run_doctor(bare_project)
        assert result["status"] == "error"

    def test_overall_ok_when_all_good(self, project_with_config: Path) -> None:
        # Even with warns (no hooks), overall should be at least warn
        result = run_doctor(project_with_config)
        assert result["status"] in ("ok", "warn")

    def test_version_fields(self, project_with_config: Path) -> None:
        result = run_doctor(project_with_config)
        assert "version" in result
        assert "python_version" in result

    def test_json_structure(self, project_with_config: Path) -> None:
        result = run_doctor(project_with_config)
        assert "checks" in result
        assert isinstance(result["checks"], list)
        for check in result["checks"]:
            assert "name" in check
            assert "message" in check
            assert "status" in check
            assert check["status"] in ("ok", "warn", "error")


class TestDoctorFormat:
    def test_format_includes_status(self, project_with_config: Path) -> None:
        result = run_doctor(project_with_config)
        output = format_doctor(result)
        assert "Doctor result:" in output

    def test_format_includes_fixes(self, bare_project: Path) -> None:
        result = run_doctor(bare_project)
        output = format_doctor(result)
        assert "Suggested actions:" in output
