"""Shared test fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dev_cycle.config import Config
from dev_cycle.cycle import start_cycle


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Create a minimal project directory with config."""
    config = {
        "project_name": "test-project",
        "cycle_root": "ops/dev-cycles",
        "version_history_file": "docs/version-history.md",
        "default_branch": "main",
        "reviewers": ["codex"],
        "store_git_diff": False,
        "store_git_status": False,
    }
    (tmp_path / "devcycle.config.json").write_text(json.dumps(config))
    (tmp_path / "ops" / "dev-cycles").mkdir(parents=True)
    (tmp_path / "docs").mkdir(parents=True)
    (tmp_path / "docs" / "version-history.md").write_text("# Version History\n")
    return tmp_path


@pytest.fixture
def cfg(tmp_project: Path) -> Config:
    """Load config from tmp_project."""
    return Config.load(tmp_project)


@pytest.fixture
def cycle_dir(cfg: Config) -> Path:
    """Create a cycle and return its directory."""
    return start_cycle(cfg, "v0.1.0", "test cycle")


SAMPLE_REVIEW_UNSTRUCTURED = """\
Overall good code quality.
- Critical: missing input validation on user data
- Should add error handling for network failures
- Consider using constants instead of magic numbers
- Minor typo in variable name
"""

SAMPLE_REVIEW_STRUCTURED = """\
# Codex Review

## Summary
Solid implementation with a few issues.

## Findings

### High
- Missing input validation on user data

### Medium
- Should add error handling for network failures
- Consider using constants instead of magic numbers

### Low
- Minor typo in variable name

## Raw Notes
Reviewed on 2026-03-31.
"""
