# Self-Hosting Guide

This project uses its own dev cycle framework.

## Setup

```bash
pip install -e .
devcycle doctor        # check environment
devcycle setup-hooks   # install git hooks
source <(devcycle completion bash)  # optional: shell completion
```

## Branch Strategy

- Small fix → same branch is fine
- New feature or larger change → create a feature branch
- `doctor` warns if you're on main or have a dirty tree
- One cycle per branch is the simplest approach

```bash
git checkout -b feat/my-change
devcycle run --version v0.2.0 --title "my change"
# ... cycle completes ...
git push && create PR
```

## Full Cycle (Orchestrator)

```bash
# Recommended: use `run` for the full guided flow
git checkout -b feat/your-change
devcycle run --version v0.2.0 --title "your change"
devcycle resume    # if interrupted
devcycle status    # to check progress
```

## Full Cycle (Manual)

```bash
# 1. Start
devcycle start --version v0.2.0 --title "your change"

# 2. Implement + fill request.md + fill claude-implementation-summary.md

# 3. Prepare (prints Codex prompt + import commands)
devcycle prepare

# 4. Run Codex review (HUMAN), save to codex-output.txt

# 5. Import + finalize + generate followup
cat codex-output.txt | devcycle review-loop --generate-followup

# 6. Edit codex-followup.md — accept/defer/reject
# 7. Implement accepted fixes

# 8. Check status
devcycle next

# 9. If re-review recommended → devcycle prepare (back to 3)
# 9. If not → finalize

# 10. Check + finalize
devcycle check
devcycle finalize --strict
```

## Lost?

```bash
devcycle next
```

## Quick Codex Handoff

```bash
devcycle handoff         # human-readable
devcycle handoff --json  # machine-readable
```

## Re-review Decision

| Accepted findings | Hint | Action |
|-------------------|------|--------|
| HIGH items | `recommended` | `devcycle prepare` |
| MEDIUM only | `optional` | Your call |
| LOW / none | `not_needed` | `devcycle finalize` |

## --strict

`devcycle check` = preview. `devcycle finalize --strict` = enforce.
Both check: all 5 files filled + final-summary has Overview + Changes.

## JSON Output

All key commands support `--json`:

```bash
devcycle start --version v --title t --json
devcycle prepare --json
devcycle handoff --json
devcycle import-review --from-file f --json
devcycle followup --json
devcycle review-loop --from-file f --json
devcycle check --json
devcycle next --json
devcycle finalize --json
```

## Light Changes

```bash
devcycle start --version v0.2.1 --title "fix typo"
# fix...
devcycle finalize
```

## Phase Reference

| Phase | Next |
|-------|------|
| `started` | `prepare` |
| `review_pending` | `review-loop` |
| `review_imported` | `finalize-review` |
| `review_done` | `followup` |
| `followup_done` | `check` → `finalize --strict` |
| `completed` | `start` |
