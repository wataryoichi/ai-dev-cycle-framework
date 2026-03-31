"""Terminal interaction for decision points."""

from __future__ import annotations

import sys

from .state_machine import Choice


def prompt_choice(choices: list[Choice], header: str = "") -> Choice:
    """Display numbered choices with a default. Enter selects the default."""
    if header:
        print(header, file=sys.stderr)
        print(file=sys.stderr)

    default = choices[0] if choices else None

    for c in choices:
        marker = " *" if c is default else ""
        print(f"  {c.key}. {c.label}{marker}", file=sys.stderr)
    print(file=sys.stderr)

    prompt_text = f"Choose [1-{len(choices)}, Enter={default.key}]: " if default else "Choose: "

    while True:
        try:
            raw = input(prompt_text).strip()
        except (EOFError, KeyboardInterrupt):
            print(file=sys.stderr)
            for c in choices:
                if c.action == "exit":
                    return c
            return choices[-1]

        if raw == "" and default:
            return default

        try:
            num = int(raw)
            for c in choices:
                if c.key == num:
                    return c
            print(f"  Invalid: {num}", file=sys.stderr)
        except ValueError:
            print(f"  Enter a number (1-{len(choices)}) or press Enter for default", file=sys.stderr)


def prompt_review_input() -> str:
    """Ask for review text — file path, paste, or empty to exit."""
    print("Provide Codex review output:", file=sys.stderr)
    print("  Enter a file path, or 'paste' to type/paste directly.", file=sys.stderr)
    print("  Press Enter with no input to exit (resume later).", file=sys.stderr)
    print(file=sys.stderr)

    try:
        raw = input("File path, 'paste', or Enter to skip: ").strip()
    except (EOFError, KeyboardInterrupt):
        print(file=sys.stderr)
        return ""

    if not raw:
        return ""

    if raw.lower() == "paste":
        print("Paste review text, then press Ctrl+D:", file=sys.stderr)
        try:
            return sys.stdin.read()
        except (EOFError, KeyboardInterrupt):
            return ""

    from pathlib import Path
    p = Path(raw)
    if p.exists():
        content = p.read_text()
        if content.strip():
            return content
        print(f"  File is empty: {raw}", file=sys.stderr)
        return ""

    print(f"  File not found: {raw}", file=sys.stderr)
    return ""


def prompt_confirm(message: str) -> bool:
    """Simple y/n confirmation."""
    try:
        raw = input(f"{message} [y/N]: ").strip().lower()
        return raw in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False
