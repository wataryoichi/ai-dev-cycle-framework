# AI Dev Cycle Framework

A framework for structured AI-assisted development cycles. Claude implements, Codex reviews, and every cycle is logged for traceability.

## Overview

This framework provides:

- **Structured cycles** — each unit of work gets a dedicated directory with standardized artifacts
- **Implementation tracking** — requests, summaries, reviews, and follow-ups are recorded
- **Review integration** — Codex review results are captured and systematically addressed
- **Version history** — cumulative log of all changes across versions
- **CLI tooling** — simple commands to start, finalize, and query cycles
- **Claude Code commands** — slash commands for seamless workflow integration

## Quick Start

### 1. Add configuration

Create `devcycle.config.json` in your project root:

```json
{
  "project_name": "your-project",
  "cycle_root": "ops/dev-cycles",
  "version_history_file": "docs/version-history.md",
  "default_branch": "main",
  "reviewers": ["codex"],
  "store_git_diff": true,
  "store_git_status": true
}
```

### 2. Create the cycle directory

```bash
mkdir -p ops/dev-cycles
```

### 3. Start a cycle

```bash
python3 -m dev_cycle.cli start-cycle --version v0.1.0 --title "add user authentication"
```

### 4. Implement and record

- Edit `request.md` with the full goal
- Implement the changes
- Update `claude-implementation-summary.md`

### 5. Review

Run Codex review and save results to `codex-review.md` in the cycle directory.

### 6. Finalize

```bash
python3 -m dev_cycle.cli finalize-cycle --cycle-dir ops/dev-cycles/<cycle_id>
```

## CLI Reference

| Command | Description |
|---------|-------------|
| `start-cycle --version V --title T` | Create a new cycle directory with templates |
| `finalize-cycle --cycle-dir DIR` | Mark cycle complete, update index and history |
| `show-index` | List all cycles (supports `--version`, `--status`, `--format markdown`) |
| `latest-cycle` | Print the path of the most recent cycle |
| `append-history --cycle-dir DIR` | Manually append a cycle to version history |
| `setup-hooks` | Configure git to use project hooks (auto-tag) |

All commands accept `--project-root` to specify a different project root.

## Version Tag Automation

A post-commit hook automatically creates git tags when the commit message starts
with `vX.Y.Z`.

### Setup

```bash
python3 -m dev_cycle.cli setup-hooks   # or: make setup
```

This sets `core.hooksPath` to `scripts/hooks/`, enabling the auto-tag hook.

### Usage

```bash
git commit -m "v0.2.0: add show-index filtering"
# → [auto-tag] Created tag: v0.2.0

git push --follow-tags   # pushes commit + tag together
```

- Only triggers when the message starts with `vX.Y.Z`
- Skips if the tag already exists
- Normal commits (no version prefix) are unaffected

## Cycle Artifacts

Each cycle directory contains:

```
ops/dev-cycles/<cycle_id>/
  meta.json                          # Cycle metadata
  request.md                         # What was requested
  claude-implementation-summary.md   # What was implemented
  codex-review.md                    # Review findings
  codex-followup.md                  # How feedback was addressed
  final-summary.md                   # Final summary
  self-application-notes.md          # Self-hosting impact notes
  git-status.txt                     # Git status snapshot
  git.diff                           # Git diff snapshot
```

## Claude Code Commands

Copy `.claude/commands/` to your project to get these slash commands:

| Command | Purpose |
|---------|---------|
| `/devcycle-start` | Start a new cycle |
| `/devcycle-finalize` | Finalize the current cycle |
| `/devcycle-review-fix` | Process Codex review feedback |
| `/devcycle-full-loop` | Guided full cycle from start to finish |

## Using the Framework on Itself

This project is a **self-applying framework** — it uses its own dev cycle tooling
to manage its own development.

### How it works

The repository ships with `devcycle.config.json` pre-configured for self-application.
Every improvement to the framework is tracked as a cycle in `ops/dev-cycles/`, using
the same CLI and commands that any other project would use.

### Self-application setup

No special setup is needed. The config, commands, and directories are already in place.

### Typical self-development loop

```bash
# 1. Start a cycle
python3 -m dev_cycle.cli start-cycle --version v0.1.0 --title "add show-index filtering"

# 2. Implement the feature (Claude or manual)

# 3. Run Codex review on the changes

# 4. Address review feedback

# 5. Finalize
python3 -m dev_cycle.cli finalize-cycle --cycle-dir $(python3 -m dev_cycle.cli latest-cycle)
```

### Generated logs

Self-application cycles produce the same artifacts as any project. The
`self-application-notes.md` file is used to note whether a cycle improves the
framework's features or its own development workflow.

### Constraints

- The first few cycles may involve manual steps as the framework bootstraps.
- Self-application uses the same config structure — no special-case logic.
- Cycle logs in `ops/dev-cycles/` serve double duty as both development records
  and usage examples for the framework.

### Further reading

- [Self-Hosting Guide](docs/self-hosting.md) — detailed setup and workflow
- [Operational Playbook](docs/operational-playbook.md) — day-to-day rules

## Project Structure

```
.claude/commands/          # Claude Code slash commands
dev_cycle/                 # Python package (CLI + core logic)
docs/                      # Documentation
  self-hosting.md          # Self-application guide
  operational-playbook.md  # Operational rules
  version-history.md       # Cumulative version log
ops/dev-cycles/            # Cycle log storage
scripts/hooks/             # Git hooks (auto-tag)
devcycle.config.json       # Self-application config
Makefile                   # Setup shortcuts
```

## License

MIT
