"""Terminal interaction for decision points."""

from __future__ import annotations

import sys
from typing import Callable

from .state_machine import Choice


def prompt_choice(choices: list[Choice], header: str = "") -> Choice:
    """Display numbered choices, return the selected one."""
    if header:
        print(header, file=sys.stderr)
        print(file=sys.stderr)
    for c in choices:
        print(f"  {c.key}. {c.label}", file=sys.stderr)
    print(file=sys.stderr)

    while True:
        try:
            raw = input("Choose [number]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print(file=sys.stderr)
            # Default to exit if available
            for c in choices:
                if c.action == "exit":
                    return c
            return choices[-1]

        try:
            num = int(raw)
            for c in choices:
                if c.key == num:
                    return c
            print(f"  Invalid choice: {num}", file=sys.stderr)
        except ValueError:
            print(f"  Enter a number (1-{len(choices)})", file=sys.stderr)


def prompt_review_input() -> str:
    """Ask for review text — file path or direct input."""
    print("Provide Codex review results:", file=sys.stderr)
    print("  1. Enter file path", file=sys.stderr)
    print("  2. Paste text (end with Ctrl+D)", file=sys.stderr)
    print(file=sys.stderr)

    try:
        raw = input("File path or 'paste': ").strip()
    except (EOFError, KeyboardInterrupt):
        print(file=sys.stderr)
        return ""

    if raw.lower() == "paste":
        print("Paste review text, then press Ctrl+D:", file=sys.stderr)
        return sys.stdin.read()

    from pathlib import Path
    p = Path(raw)
    if p.exists():
        return p.read_text()

    print(f"  File not found: {raw}", file=sys.stderr)
    return ""


def prompt_confirm(message: str) -> bool:
    """Simple y/n confirmation."""
    try:
        raw = input(f"{message} [y/N]: ").strip().lower()
        return raw in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False
