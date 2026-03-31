# AI Dev Cycle Framework

Claude→Codex→Claude orchestrator with automatic version management.  
Build fast, break things, roll back instantly.

## Install

```bash
pip install -e .
devcycle doctor
```

## Turbo Mode

The fast path. Auto commits, tags, and pushes every change.

```bash
devcycle turbo --title "build first prototype"
devcycle turbo --title "improve review loop"
devcycle turbo --title "fix edge case in parser"
```

Each call:
1. Creates a cycle with auto-generated version (`dev-YYYYMMDD-HHMMSS`)
2. Commits all changes
3. Tags with `devcycle/dev-YYYYMMDD-HHMMSS`
4. Pushes to remote

### Rollback

Made a mistake? Roll back:

```bash
devcycle rollback              # undo last commit
devcycle rollback --steps 3    # go back 3 commits
devcycle rollback --to devcycle/dev-20260331-153002  # specific version
```

### History

```bash
devcycle history               # recent versions
devcycle history --json        # machine-readable
devcycle history --limit 50    # more entries
```

### No-push mode

```bash
devcycle turbo --title "experiment" --no-push
```

## Guided Mode

For step-by-step control with interactive prompts:

```bash
devcycle run --version v0.1.0 --title "add auth"
devcycle resume    # continue interrupted cycle
devcycle status    # show current state
```

## All Commands

### Turbo

| Command | Description |
|---------|-------------|
| `turbo` | Fast cycle: auto version/commit/tag/push |
| `rollback` | Revert to previous version |
| `history` | Show recent versions and tags |

### Guided

| Command | Description |
|---------|-------------|
| `run` | Interactive cycle with decision prompts |
| `resume` | Continue interrupted cycle |
| `status` | Show state, progress, quality |

### Manual (advanced)

| Command | Description |
|---------|-------------|
| `start` | Start a cycle manually |
| `prepare` | Prepare for review |
| `review-loop` | Import review (all-in-one) |
| `followup` | Generate followup draft |
| `check` | Quality report |
| `finalize` | Complete cycle |
| `next` | Show next command |

### Utilities

| Command | Description |
|---------|-------------|
| `doctor` | Check environment |
| `completion` | Shell completion (bash/zsh) |
| `handoff` | Show Codex prompt |
| `index` | List cycles |
| `latest` | Latest cycle path |

All commands support `--json`.

## Safety Model

Turbo mode is safe because you can always roll back:

```
turbo → commit → tag → push → (oops) → rollback → push
```

Every change is tagged. `devcycle history` shows what happened.  
`devcycle rollback` undoes it.

## Shell Completion

```bash
source <(devcycle completion bash)
source <(devcycle completion zsh)
```

## Self-Hosting

This project uses its own tooling. See [docs/self-hosting.md](docs/self-hosting.md).

## License

MIT
