# AI Dev Cycle Framework

Claude→Codex→Claude orchestrator. Run full development cycles, auto-commit,
auto-tag, auto-push. Roll back instantly when things break.

## Install

```bash
pip install -e .
devcycle doctor
```

## Turbo Mode

```bash
devcycle turbo --title "build first prototype"
```

What happens:
1. Creates cycle with auto version (`dev-YYYYMMDD-HHMMSS`)
2. Runs orchestrator (Claude→Codex→Claude state machine)
3. If `DEVCYCLE_CLAUDE_CMD` is set, auto-runs Claude implementation
4. If `DEVCYCLE_CODEX_CMD` is set, auto-runs Codex review + import
5. At human-decision points, prompts with numbered choices
6. Auto-commits, tags (`devcycle/dev-...`), pushes

### AI Runner Setup

```bash
# Optional — turbo works without these (blocks at AI steps)
export DEVCYCLE_CLAUDE_CMD="claude --print"
export DEVCYCLE_CODEX_CMD="codex review --prompt"
```

Without these, turbo pauses at implementing/review and asks for manual input.

### Options

```bash
devcycle turbo --title "..." --no-push          # commit+tag only
devcycle turbo --title "..." --non-interactive   # auto-advance, block where needed
devcycle turbo --title "..." --dry-run           # preview, don't execute
```

### Rollback

```bash
devcycle rollback                  # undo last commit
devcycle rollback --steps 3        # go back 3 commits
devcycle rollback --to devcycle/dev-20260331-153002
devcycle rollback --reason "broke auth"
```

Rollbacks are recorded in `ops/rollbacks/` (Markdown + JSON).

### History

```bash
devcycle history
devcycle history --json
```

## Guided Mode

Step-by-step with interactive prompts:

```bash
devcycle run --version v0.1.0 --title "add auth"
devcycle resume
devcycle status
```

## Commands

| Command | Description |
|---------|-------------|
| **`turbo`** | Full cycle + auto commit/tag/push |
| **`rollback`** | Revert to previous version |
| **`history`** | Show recent versions |
| `run` | Interactive guided cycle |
| `resume` | Continue interrupted cycle |
| `status` | Show state and progress |
| `doctor` | Check environment |
| `completion` | Shell completion |

Advanced: `start`, `prepare`, `review-loop`, `followup`, `check`, `finalize`, `next`

All commands support `--json`.

## What's Automated

| Phase | Automated? | Requires |
|-------|-----------|----------|
| Cycle creation | Yes | — |
| Claude implementation | Yes (if configured) | `DEVCYCLE_CLAUDE_CMD` |
| Review preparation | Yes | — |
| Codex review | Yes (if configured) | `DEVCYCLE_CODEX_CMD` |
| Review import + followup | Yes | — |
| Accept/defer/reject | No — human decision | Choice UI |
| Fix implementation | Prompted | — |
| Commit/tag/push | Yes | — |
| Rollback | Yes | — |

## Dual Output

Each cycle produces Markdown (human) + JSON (machine):

```
ops/dev-cycles/<cycle_id>/
  meta.json / request.json / review.json / followup.json / final_summary.json
  request.md / codex-review.md / codex-followup.md / final-summary.md
  claude-implementation-summary.md
```

Rollbacks: `ops/rollbacks/rollback-YYYYMMDD-HHMMSS.{json,md}`

## Safety = Rollback

Every `turbo` tags the result. `rollback` reverts to any tag.

```bash
devcycle turbo --title "risky change"
# oops
devcycle rollback
```

## Self-Hosting

See [docs/self-hosting.md](docs/self-hosting.md).

## License

MIT
