# AI Dev Cycle Framework

Claude→Codex→Claude orchestrator. Run full development cycles, auto-commit,
auto-tag, auto-push. Roll back instantly when things break.

## Install

```bash
pip install -e .
devcycle doctor
```

## Turbo Mode

The main way to use this. Runs the full cycle then auto-commits.

```bash
devcycle turbo --title "build first prototype"
```

What happens:
1. Creates a cycle with auto-generated version
2. Runs the orchestrator (Claude→Codex→Claude state machine)
3. At decision points, prompts you with numbered choices
4. When done (or paused), auto-commits all changes
5. Tags with `devcycle/dev-YYYYMMDD-HHMMSS`
6. Pushes to remote

### Options

```bash
devcycle turbo --title "experiment" --no-push        # commit+tag only
devcycle turbo --title "ci run" --non-interactive    # auto-advance, block where needed
devcycle turbo --title "preview" --dry-run           # show plan, don't execute
```

### Rollback

```bash
devcycle rollback              # undo last commit
devcycle rollback --steps 3    # go back 3 commits
devcycle rollback --to devcycle/dev-20260331-153002
```

### History

```bash
devcycle history               # recent versions with tags
devcycle history --json        # machine-readable
```

## Guided Mode

For step-by-step control with interactive prompts at every decision:

```bash
devcycle run --version v0.1.0 --title "add auth"
devcycle resume    # continue interrupted cycle
devcycle status    # show current state
```

Non-interactive:

```bash
devcycle run --non-interactive --version v0.1.0 --title "auto"
```

## Commands

### Turbo (primary)

| Command | Description |
|---------|-------------|
| `turbo` | Full cycle + auto commit/tag/push |
| `rollback` | Revert to previous version |
| `history` | Show recent versions |

### Guided

| Command | Description |
|---------|-------------|
| `run` | Interactive cycle with decision prompts |
| `resume` | Continue interrupted cycle |
| `status` | Show state and progress |

### Manual (advanced)

| Command | Description |
|---------|-------------|
| `start` | Start cycle | `prepare` | Prepare review |
| `review-loop` | Import review | `followup` | Generate followup |
| `check` | Quality report | `finalize` | Complete cycle |

### Utilities

| Command | Description |
|---------|-------------|
| `doctor` | Check environment |
| `completion` | Shell completion |
| `rollback` | Revert changes |
| `history` | Version log |

All commands support `--json`.

## How Turbo Works

```
turbo start → orchestrator loop → [decision points] → commit → tag → push
                                        ↑
                            Claude implements
                            Codex reviews
                            Claude fixes
                            You make decisions
```

The orchestrator auto-advances through safe states (prepare review, generate
followup) and pauses at decision points (implementation done? fix decisions?
finalize mode?). At each pause, press Enter for the recommended choice.

## Safety = Rollback

Turbo mode is aggressive. Safety comes from easy rollback, not from gates.

Every `turbo` call tags the result. `rollback` reverts to any tag.
`history` shows what happened.

```bash
devcycle turbo --title "risky change"    # auto-commit+tag
# oops, broke something
devcycle rollback                        # instant undo
```

## Self-Hosting

This project uses its own tooling. See [docs/self-hosting.md](docs/self-hosting.md).

## License

MIT
