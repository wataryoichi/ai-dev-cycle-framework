"""Configuration loading for dev cycle framework."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_CONFIG_NAME = "devcycle.config.json"

DEFAULTS = {
    "cycle_root": "ops/dev-cycles",
    "version_history_file": "docs/version-history.md",
    "default_branch": "main",
    "reviewers": ["codex"],
    "store_git_diff": True,
    "store_git_status": True,
}


@dataclass
class Config:
    project_name: str
    cycle_root: str = DEFAULTS["cycle_root"]
    version_history_file: str = DEFAULTS["version_history_file"]
    default_branch: str = DEFAULTS["default_branch"]
    reviewers: list[str] = field(default_factory=lambda: list(DEFAULTS["reviewers"]))
    store_git_diff: bool = True
    store_git_status: bool = True
    project_root: Path = field(default_factory=Path.cwd)

    @classmethod
    def load(cls, project_root: Path | None = None) -> Config:
        root = project_root or Path.cwd()
        config_path = root / DEFAULT_CONFIG_NAME
        if not config_path.exists():
            raise FileNotFoundError(
                f"No {DEFAULT_CONFIG_NAME} found in {root}. "
                "Run in your project root or create the config file."
            )
        with open(config_path) as f:
            data = json.load(f)
        return cls(
            project_name=data["project_name"],
            cycle_root=data.get("cycle_root", DEFAULTS["cycle_root"]),
            version_history_file=data.get("version_history_file", DEFAULTS["version_history_file"]),
            default_branch=data.get("default_branch", DEFAULTS["default_branch"]),
            reviewers=data.get("reviewers", list(DEFAULTS["reviewers"])),
            store_git_diff=data.get("store_git_diff", True),
            store_git_status=data.get("store_git_status", True),
            project_root=root,
        )

    @property
    def cycle_root_path(self) -> Path:
        return self.project_root / self.cycle_root

    @property
    def version_history_path(self) -> Path:
        return self.project_root / self.version_history_file
