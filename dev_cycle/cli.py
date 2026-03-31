"""CLI entry point for the dev cycle framework."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import Config
from .cycle import find_latest_cycle, finalize_cycle, load_index, start_cycle


def cmd_start_cycle(args: argparse.Namespace) -> None:
    cfg = Config.load(Path(args.project_root))
    cycle_dir = start_cycle(cfg, args.version, args.title)
    print(f"Cycle started: {cycle_dir}")


def cmd_finalize_cycle(args: argparse.Namespace) -> None:
    cfg = Config.load(Path(args.project_root))
    cycle_dir = Path(args.cycle_dir)
    if not cycle_dir.is_absolute():
        cycle_dir = cfg.project_root / cycle_dir
    finalize_cycle(cfg, cycle_dir)
    print(f"Cycle finalized: {cycle_dir}")


def cmd_show_index(args: argparse.Namespace) -> None:
    cfg = Config.load(Path(args.project_root))
    entries = load_index(cfg)

    if args.version:
        entries = [e for e in entries if e.get("version") == args.version]
    if args.status:
        entries = [e for e in entries if e.get("status") == args.status]

    if not entries:
        print("No cycles found.")
        return

    if args.format == "markdown":
        print("| Cycle ID | Version | Title | Status |")
        print("|----------|---------|-------|--------|")
        for e in entries:
            print(f"| `{e['cycle_id']}` | {e['version']} | {e['title']} | {e['status']} |")
    else:
        for e in entries:
            print(json.dumps(e))


def cmd_latest_cycle(args: argparse.Namespace) -> None:
    cfg = Config.load(Path(args.project_root))
    latest = find_latest_cycle(cfg)
    if latest:
        print(latest)
    else:
        print("No cycles found.", file=sys.stderr)
        sys.exit(1)


def cmd_setup_hooks(args: argparse.Namespace) -> None:
    import subprocess
    root = Path(args.project_root).resolve()
    hooks_dir = root / "scripts" / "hooks"
    if not hooks_dir.exists():
        print(f"No scripts/hooks/ directory in {root}", file=sys.stderr)
        sys.exit(1)
    try:
        subprocess.run(
            ["git", "config", "core.hooksPath", "scripts/hooks"],
            cwd=root, check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Failed to configure hooks: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"Git hooks path set to scripts/hooks/")
    hook = hooks_dir / "post-commit"
    if hook.exists():
        print(f"  post-commit: auto-tag on vX.Y.Z commit messages")


def cmd_append_history(args: argparse.Namespace) -> None:
    cfg = Config.load(Path(args.project_root))
    cycle_dir = Path(args.cycle_dir)
    if not cycle_dir.is_absolute():
        cycle_dir = cfg.project_root / cycle_dir
    meta_path = cycle_dir / "meta.json"
    if not meta_path.exists():
        print(f"No meta.json in {cycle_dir}", file=sys.stderr)
        sys.exit(1)
    meta = json.loads(meta_path.read_text())
    from .cycle import _append_version_history
    _append_version_history(cfg, meta, cycle_dir)
    print(f"Appended to {cfg.version_history_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="devcycle",
        description="AI Dev Cycle Framework CLI",
    )
    parser.add_argument(
        "--project-root", default=".",
        help="Project root directory (default: current directory)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # start-cycle
    p = sub.add_parser("start-cycle", help="Start a new development cycle")
    p.add_argument("--version", required=True, help="Version label (e.g. v0.1.0)")
    p.add_argument("--title", required=True, help="Short cycle title")
    p.set_defaults(func=cmd_start_cycle)

    # finalize-cycle
    p = sub.add_parser("finalize-cycle", help="Finalize a completed cycle")
    p.add_argument("--cycle-dir", required=True, help="Path to cycle directory")
    p.set_defaults(func=cmd_finalize_cycle)

    # show-index
    p = sub.add_parser("show-index", help="Show cycle index")
    p.add_argument("--version", default=None, help="Filter by version")
    p.add_argument("--status", default=None, help="Filter by status (started/completed)")
    p.add_argument("--format", default="jsonl", choices=["jsonl", "markdown"],
                    help="Output format")
    p.set_defaults(func=cmd_show_index)

    # latest-cycle
    p = sub.add_parser("latest-cycle", help="Print path of most recent cycle")
    p.set_defaults(func=cmd_latest_cycle)

    # setup-hooks
    p = sub.add_parser("setup-hooks", help="Configure git to use project hooks (auto-tag)")
    p.set_defaults(func=cmd_setup_hooks)

    # append-history
    p = sub.add_parser("append-history", help="Append cycle to version history")
    p.add_argument("--cycle-dir", required=True, help="Path to cycle directory")
    p.set_defaults(func=cmd_append_history)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
