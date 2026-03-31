# AI Dev Cycle Framework

Claude→Codex→Claude orchestrator. Auto commit/tag/push. Roll back instantly.
Multi-cycle. Japanese/English output.

## Install

```bash
pip install -e .
devcycle doctor
```

## Turbo Mode

```bash
devcycle turbo --title "build prototype"
devcycle turbo --title "プロトタイプ構築" --lang ja
devcycle turbo --title "iterate on review" --cycles 3
```

### Options

| Flag | Description |
|------|-------------|
| `--title` | What this cycle does (required) |
| `--spec` | Path to spec file (default: docs/spec.md) |
| `--lang {en,ja}` | Output language for Markdown files |
| `--cycles N` | Run N cycles consecutively |
| `--no-push` | Commit+tag only, skip push |
| `--non-interactive` | Auto-advance, block where input needed |
| `--dry-run` | Preview without executing |
| `--json` | Machine-readable output |

### AI Runners

```bash
export DEVCYCLE_CLAUDE_CMD="claude --print"
export DEVCYCLE_CODEX_CMD="codex review --prompt"
```

### Rollback / History

```bash
devcycle rollback
devcycle rollback --to devcycle/dev-20260401-120000
devcycle history
```

## Guided Mode

```bash
devcycle run --version v0.1.0 --title "add auth" --lang ja --spec docs/spec.md
devcycle resume
devcycle status
```

## Commands

| Command | Description |
|---------|-------------|
| **`turbo`** | Full cycle + auto git (`--cycles`, `--lang`) |
| **`rollback`** | Revert to previous version |
| **`history`** | Recent versions |
| `run` | Interactive guided cycle |
| `resume` | Continue cycle |
| `status` | Show state |
| `doctor` | Check environment |

## Multi-cycle

```bash
devcycle turbo --title "improve calculator" --cycles 3 --no-push
```

Each cycle:
1. Auto-versions (`dev-YYYYMMDD-HHMMSS`)
2. Carries forward context from previous cycle
3. Commits + tags after each cycle
4. Stops on block or after N cycles

## Language

```bash
devcycle turbo --title "電卓の改善" --lang ja
```

Markdown output (request.md, summary, followup) uses Japanese headings.
JSON keys stay English for machine readability.

## Self-Hosting

See [docs/self-hosting.md](docs/self-hosting.md).

## License

MIT
