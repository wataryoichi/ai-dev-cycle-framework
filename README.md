# AI Dev Cycle Framework

Claude→Codex→Claude orchestrator. Auto commit/tag/push. Roll back instantly.
Multi-cycle with auto-fix loop. Japanese/English output. GitHub publish.

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
devcycle turbo --title "tetris game" --cycles 3 --github
```

What happens with both runners configured:
1. Creates cycle with auto version + spec detection
2. **Claude runner** auto-implements (or blocks for manual input)
3. **Codex runner** auto-reviews via `codex review -` (stdin)
4. Findings parsed by severity, followup draft generated
5. **Auto-fix loop**: Claude fixes findings → Codex re-reviews → repeat
6. Stable detection: stops when findings reach zero
7. No-progress detection: stops when findings don't change after fix
8. Auto-generates `final-summary.md` and project `README.md`
9. Auto-commits, tags, pushes after each cycle
10. Optionally creates a GitHub repo (`--github`)

### Verified E2E Flow

```
── Cycle 1/3 ──
  → Claude implementation complete
  → Prepare review and hand off to Codex
  → Codex review auto-imported
  → Generate followup draft (2 findings)
  → Auto-fixing 2 finding(s)...
  → Fix applied
  → README.md generated
  Commit: abc1234
  Tag: devcycle/dev-20260401-052317
  Pushed
```

### Options

| Flag | Description |
|------|-------------|
| `--title` | What this cycle does (required) |
| `--spec` | Spec file path (default: docs/spec.md) |
| `--lang {en,ja}` | Output language for Markdown |
| `--cycles N` | Run N cycles consecutively |
| `--max-fix-rounds N` | Max fix+rereview rounds per cycle (default: 3) |
| `--github` | Create a GitHub repo and push the result |
| `--no-push` | Commit+tag only |
| `--non-interactive` | Auto-advance, block where input needed |
| `--dry-run` | Preview without executing |
| `--json` | Machine-readable output |

### Rollback / History

```bash
devcycle rollback
devcycle history
```

## Auto-fix Loop

When Codex finds issues, the framework automatically:
1. Builds a fix plan from review findings (`fix_plan.json`)
2. Sends Claude a targeted fix prompt
3. Triggers a Codex re-review
4. Repeats until stable (0 findings) or no-progress detected

Control with `--max-fix-rounds N` (default: 3).

Stopped reasons:
- `stable` — no findings after fix
- `no_progress` — same findings after fix+rereview
- `max_fix_rounds_reached` — fix limit hit
- `blocked` — human input needed

## Multi-cycle

```bash
devcycle turbo --title "improve calculator" --cycles 3 --no-push
```

Each cycle carries forward context from the previous:
- Previous implementation summary
- Outstanding review findings
- Spec path and digest

Chain summary saved as `run_summary.json` + `run_summary.md`.

## Auto-generated Files

Each cycle automatically produces:
- `final-summary.md` — overview, changes, verification, remaining issues
- `README.md` (project root) — title, description, artifact list for GitHub

## Prompt Artifacts

Each cycle saves the prompts sent to AI runners:
- `claude-prompt.txt` — what Claude received (includes spec + carry-forward)
- `codex-prompt.txt` — what Codex received (includes acceptance criteria)
- `claude-fix-prompt.txt` — what Claude received for fix rounds

## Dual Output

Every record is both Markdown (human) + JSON (machine):

```
ops/dev-cycles/<cycle_id>/
  meta.json / request.json / review.json / followup.json
  implementation_summary.json / final_summary.json
  request.md / codex-review.md / codex-followup.md
  claude-implementation-summary.md / final-summary.md
  claude-prompt.txt / codex-prompt.txt / claude-fix-prompt.txt
  fix_plan.json / findings_diff.json
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
