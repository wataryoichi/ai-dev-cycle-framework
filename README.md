# AI Dev Cycle Framework

Headless AI code review and fix orchestration for unattended workflows.

Claude→Codex→Claude multi-cycle runner with audit trail, auto-fix loop, and machine-readable output. Built for CI, batch execution, and scheduled maintenance — not as a replacement for interactive development.

## When to use devcycle

- **Nightly code review** — run against your repos while you sleep
- **PR auto-review** — Claude implements, Codex reviews, Claude fixes, repeat
- **Batch processing** — iterate multiple cycles across projects unattended
- **Audit trails** — every prompt, review, finding, and fix decision is recorded
- **Scheduled maintenance** — cron/CI-driven quality checks with standardized output

## When NOT to use devcycle

Use **Claude Code + Codex plugin** directly when you're actively developing and want interactive, high-quality, human-in-the-loop results. devcycle is for when humans aren't in the loop.

## Install

```bash
pip install -e .
devcycle doctor
```

## Setup AI Runners

```bash
# Required: Codex for review
export DEVCYCLE_CODEX_CMD="codex review"

# Optional: Claude for implementation + auto-fix
export DEVCYCLE_CLAUDE_CMD="claude --print"
```

## Quick Start

```bash
# Single unattended cycle
devcycle turbo --title "refactor auth module" --no-push

# Multi-cycle with auto-fix loop (Japanese output)
devcycle turbo --title "認証モジュールのリファクタ" --lang ja --cycles 3

# Continue iterating on a previous cycle
devcycle turbo --title "address remaining findings" --continue-from <cycle_id>

# Generate project and publish to GitHub
devcycle turbo --title "tetris game" --github
```

## How It Works

```
┌─────────────────────────────────────────────────┐
│                  devcycle turbo                  │
│                                                 │
│  1. Create cycle (version, spec, request)       │
│  2. Claude implements                           │
│  3. Codex reviews → findings by severity        │
│  4. Auto-fix loop:                              │
│     Claude fixes → Codex re-reviews → repeat    │
│  5. Stop condition:                             │
│     ✓ stable (0 findings)                       │
│     ✗ no_progress (same findings after fix)     │
│     ✗ max_fix_rounds reached                    │
│  6. Commit + tag + push                         │
│  7. Next cycle (if --cycles > 1)                │
└─────────────────────────────────────────────────┘
```

## Machine-Readable Output

Every run produces structured artifacts for CI integration:

```bash
# JSON output mode
devcycle turbo --title "review" --json

# Exit codes
# 0 = completed successfully
# 2 = blocked (human input needed or no-progress)
```

### Stopped Reasons

| Reason | Meaning |
|--------|---------|
| `stable` | No findings after fix — clean |
| `completed` | Cycle finished normally |
| `no_progress` | Same findings after fix+rereview |
| `max_fix_rounds_reached` | Fix attempt limit hit |
| `max_cycles_reached` | All requested cycles done |
| `blocked` | Human input required |

### Artifacts per Cycle

```
ops/dev-cycles/<cycle_id>/
  meta.json                          # cycle metadata
  request.json / request.md          # what was requested
  claude-prompt.txt                  # prompt sent to Claude
  codex-prompt.txt                   # prompt sent to Codex
  claude-fix-prompt.txt              # fix prompt (if auto-fix ran)
  implementation_summary.json / .md  # what Claude built
  codex-review.md / review.json      # Codex findings
  codex-followup.md / followup.json  # followup decisions
  fix_plan.json                      # structured fix plan
  findings_diff.json                 # before/after findings comparison
  final-summary.md / .json           # auto-generated summary
  run_summary.json / .md             # multi-cycle chain summary
```

## Options

| Flag | Description |
|------|-------------|
| `--title` | What this cycle does (required) |
| `--spec` | Spec file path (default: docs/spec.md) |
| `--lang {en,ja}` | Output language for Markdown |
| `--cycles N` | Run N cycles consecutively |
| `--max-fix-rounds N` | Max fix+rereview rounds per cycle (default: 3) |
| `--continue-from ID` | Build on a previous cycle's artifacts |
| `--github` | Create a GitHub repo and push the result |
| `--no-push` | Commit+tag only |
| `--json` | Machine-readable JSON output |
| `--dry-run` | Preview without executing |

## Commands

| Command | Description |
|---------|-------------|
| **`turbo`** | Headless cycle: implement → review → fix → commit |
| **`rollback`** | Revert to a previous version |
| **`history`** | List recent versions and tags |
| **`export`** | Extract cycle artifacts to a standalone directory |
| **`doctor`** | Check environment and configuration |
| `status` | Show current cycle state |
| `run` | Interactive guided cycle |
| `resume` | Continue a paused cycle |

## GitHub Actions

```yaml
# .github/workflows/nightly-review.yml
name: Nightly AI Review
on:
  schedule:
    - cron: '0 3 * * *'  # 3am UTC
  workflow_dispatch:

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -e .
      - run: |
          devcycle turbo \
            --title "nightly review $(date +%Y-%m-%d)" \
            --cycles 2 \
            --max-fix-rounds 2 \
            --no-push \
            --json > result.json
        env:
          DEVCYCLE_CLAUDE_CMD: "claude --print"
          DEVCYCLE_CODEX_CMD: "codex review"
      - uses: actions/upload-artifact@v4
        with:
          name: devcycle-report
          path: |
            ops/dev-cycles/
            result.json
```

## Docs

- [Repositioning rationale](docs/repositioning.md) — why devcycle is a CI tool, not a dev UI
- [Operational playbook](docs/operational-playbook.md) — flow levels and conventions
- [Self-hosting](docs/self-hosting.md) — running devcycle on your own infra
- [Release checklist](docs/release-checklist.md)
- [Version history](docs/version-history.md)

## License

MIT
