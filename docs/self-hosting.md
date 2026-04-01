# Self-Hosting Guide

## Setup

```bash
pip install -e .
devcycle doctor

# Required for auto-review:
export DEVCYCLE_CODEX_CMD="codex review"
echo 'export DEVCYCLE_CODEX_CMD="codex review"' >> ~/.bashrc

# Optional for auto-implementation:
export DEVCYCLE_CLAUDE_CMD="claude --print"
```

## Full Cycle (Turbo)

```bash
devcycle turbo --title "your change" --lang ja
devcycle turbo --title "iterate" --cycles 2
devcycle resume    # if interrupted
devcycle status    # check progress
```

## What Turbo Does

1. Creates cycle + auto-detects `docs/spec.md`
2. Claude runner implements (if `DEVCYCLE_CLAUDE_CMD` set)
3. Codex runner reviews (if `DEVCYCLE_CODEX_CMD` set)
4. Followup draft auto-generated
5. Blocks at fix decisions (human needed)
6. Auto-commits, tags, pushes

## Prompt Artifacts

Each cycle saves:
- `claude-prompt.txt` — implementation prompt (includes spec + carry-forward)
- `codex-prompt.txt` — review prompt (includes acceptance criteria)

## Multi-cycle

```bash
devcycle turbo --title "improve" --cycles 3 --no-push
```

Carries forward: previous summary, outstanding findings, spec context.
Chain summary: `run_summary.json` + `run_summary.md`.

## Rollback

```bash
devcycle rollback
devcycle rollback --to devcycle/dev-20260401-120000
devcycle history
```

## Language

```bash
devcycle turbo --title "改善" --lang ja
```

Markdown headings in Japanese. JSON keys stay English.
