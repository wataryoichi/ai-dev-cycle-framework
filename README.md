# AI Dev Cycle Framework

Claude→Codex→Claude orchestrator. Auto commit/tag/push. Roll back instantly.
Multi-cycle. Japanese/English output. **Real Codex review integration verified.**

## Install

```bash
pip install -e .
devcycle doctor
```

## Setup AI Runners

```bash
# Codex review (verified working with codex-cli v0.117.0 / gpt-5.4)
export DEVCYCLE_CODEX_CMD="codex review"
echo 'export DEVCYCLE_CODEX_CMD="codex review"' >> ~/.bashrc

# Claude implementation (optional — blocks gracefully if not set)
export DEVCYCLE_CLAUDE_CMD="claude --print"
```

## Turbo Mode

```bash
devcycle turbo --title "build prototype"
devcycle turbo --title "プロトタイプ構築" --lang ja
devcycle turbo --title "iterate on review" --cycles 3
```

What happens with both runners configured:
1. Creates cycle with auto version + spec detection
2. **Claude runner** auto-implements (or blocks for manual input)
3. **Codex runner** auto-reviews via `codex review -` (stdin)
4. Findings parsed by severity, followup draft generated
5. Blocks at fix decisions (human judgment needed)
6. Auto-commits, tags, pushes after each cycle

### Verified E2E Flow

```
→ Claude implementation complete
→ Prepare review and hand off to Codex
→ Codex review auto-imported
→ Generate followup draft (1 findings)
Blocked at: fix_needed
```

Codex reviews real code, finds real issues, generates structured findings.

### Options

| Flag | Description |
|------|-------------|
| `--title` | What this cycle does (required) |
| `--spec` | Spec file path (default: docs/spec.md) |
| `--lang {en,ja}` | Output language for Markdown |
| `--cycles N` | Run N cycles consecutively |
| `--no-push` | Commit+tag only |
| `--non-interactive` | Auto-advance, block where input needed |
| `--dry-run` | Preview without executing |
| `--json` | Machine-readable output |

### Rollback / History

```bash
devcycle rollback
devcycle history
```

## Multi-cycle

```bash
devcycle turbo --title "improve calculator" --cycles 3 --no-push
```

Each cycle carries forward context from the previous:
- Previous implementation summary
- Outstanding review findings
- Spec path and digest

Chain summary saved as `run_summary.json` + `run_summary.md`.

## Prompt Artifacts

Each cycle saves the prompts sent to AI runners:
- `claude-prompt.txt` — what Claude received (includes spec + carry-forward)
- `codex-prompt.txt` — what Codex received (includes acceptance criteria)

## Dual Output

Every record is both Markdown (human) + JSON (machine):

```
ops/dev-cycles/<cycle_id>/
  meta.json / request.json / review.json / followup.json
  implementation_summary.json / final_summary.json
  request.md / codex-review.md / codex-followup.md
  claude-implementation-summary.md / final-summary.md
  claude-prompt.txt / codex-prompt.txt
```

## Commands

| Command | Description |
|---------|-------------|
| **`turbo`** | Full cycle + auto git |
| **`rollback`** | Revert to previous version |
| **`history`** | Recent versions |
| `run` | Interactive guided cycle (`--spec`, `--lang`) |
| `resume` | Continue cycle |
| `status` | Show state |
| `doctor` | Check environment |
| `completion` | Shell completion |

## Self-Hosting

See [docs/self-hosting.md](docs/self-hosting.md).

## License

MIT
