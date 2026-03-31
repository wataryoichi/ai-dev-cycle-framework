# Self-Hosting Guide

This project uses its own dev cycle framework to manage development. This document
explains how to run the framework on itself.

## Initial Setup

The repository ships with everything needed for self-application:

- `devcycle.config.json` — project-specific configuration
- `.claude/commands/` — Claude Code slash commands for the cycle workflow
- `ops/dev-cycles/` — directory where cycle logs are stored
- `docs/version-history.md` — cumulative version history

After cloning, enable the auto-tag hook:

```bash
python3 -m dev_cycle.cli setup-hooks   # or: make setup
```

This configures git to run `scripts/hooks/post-commit`, which auto-creates tags
when commit messages start with `vX.Y.Z`.

## Configuration

The self-application config lives at the repo root:

```json
{
  "project_name": "ai-dev-cycle-framework",
  "cycle_root": "ops/dev-cycles",
  "version_history_file": "docs/version-history.md",
  "default_branch": "main",
  "reviewers": ["codex"],
  "store_git_diff": true,
  "store_git_status": true
}
```

## Starting a Cycle

```bash
python3 -m dev_cycle.cli start-cycle --version v0.1.0 --title "your cycle title"
```

Or use the Claude Code command: `/devcycle-start v0.1.0 "your cycle title"`

This creates a new directory under `ops/dev-cycles/` with initial template files.

## During Implementation

1. Edit `request.md` in the cycle directory to describe the goal.
2. Implement the changes.
3. Update `claude-implementation-summary.md` with what was done.

## Codex Review

After implementation, run Codex review on the changes. Save findings to
`codex-review.md` in the cycle directory.

Then use `/devcycle-review-fix` to process the feedback:
- Accept valid items and implement fixes
- Defer out-of-scope items
- Reject inapplicable items
- Record decisions in `codex-followup.md`

## Finalizing a Cycle

```bash
python3 -m dev_cycle.cli finalize-cycle --cycle-dir ops/dev-cycles/<cycle_id>
```

Or use `/devcycle-finalize`.

This will:
- Set the cycle status to `completed`
- Capture git status and diff
- Append to `ops/dev-cycles/index.jsonl`
- Append to `docs/version-history.md`

## Viewing History

List all completed cycles:

```bash
python3 -m dev_cycle.cli show-index
```

Filter by version:

```bash
python3 -m dev_cycle.cli show-index --version v0.1.0
```

Show as a readable table:

```bash
python3 -m dev_cycle.cli show-index --format markdown
```

Find the most recent cycle:

```bash
python3 -m dev_cycle.cli latest-cycle
```

## Cycle Artifacts

Each cycle directory contains:

| File | Purpose |
|------|---------|
| `meta.json` | Cycle metadata (id, version, status, timestamps) |
| `request.md` | What was requested for this cycle |
| `claude-implementation-summary.md` | What Claude implemented |
| `codex-review.md` | Codex review findings |
| `codex-followup.md` | How review feedback was addressed |
| `final-summary.md` | Final summary with changes and remaining items |
| `self-application-notes.md` | Notes on how this cycle affects the framework itself |
| `git-status.txt` | Git status snapshot |
| `git.diff` | Git diff snapshot |

## Self-Application Notes

When a cycle modifies the framework itself, fill in `self-application-notes.md` to
record whether the change is:
- A user-facing feature improvement
- An internal tooling/workflow improvement
- A documentation or example update

This helps distinguish framework features from meta-improvements when reviewing
history.
