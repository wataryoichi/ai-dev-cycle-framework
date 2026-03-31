# Operational Playbook

## Three Flow Levels

### Light (no review)
```
devcycle start → implement → devcycle finalize
```

### Standard (with review)
```
devcycle start → implement → devcycle prepare → [Codex] →
devcycle review-loop --generate-followup → fix → devcycle check → devcycle finalize --strict
```

### Heavy (adversarial review)
Same as standard, but ask Codex to try to break things.

## When to Create a Cycle

**Always**: features, multi-file fixes, architectural changes.
**Skip**: single-file typos, dependency bumps, config-only changes.

## Re-review Rules

`devcycle next` shows a hint based on accepted findings:

| Accepted | Hint | Action |
|----------|------|--------|
| HIGH | `recommended` | `devcycle prepare` |
| MEDIUM only | `optional` | Your judgment |
| LOW / none | `not_needed` | `devcycle finalize` |

## --strict Rules

`devcycle check` = preview. `devcycle finalize --strict` = enforce.

Strict checks (all must be filled):
- `request.md`
- `claude-implementation-summary.md`
- `codex-review.md`
- `codex-followup.md`
- `final-summary.md` (must have `## Overview` + `## Changes`)

## followup — What It Generates

`devcycle followup` reads `codex-review.md` and writes `codex-followup.md`:

```markdown
## Accepted
- [HIGH] finding: <!-- action taken -->
- [MEDIUM] finding: <!-- action taken -->

## Deferred
## Rejected
```

This is a draft. Review each item, fill in actions, move items as needed.

## Human Judgment Points

- Accept / defer / reject review findings
- Code fixes for accepted findings
- Re-review decision after significant fixes

## Handling Incomplete Cycles

**Abandoned**: `devcycle finalize` with summary noting abandonment.
**Stalled**: `devcycle index --live --phase review_pending`.
**Parallel**: `--cycle-dir` to target specific cycles.

## Commit Conventions

```bash
git commit -m "v0.2.0: add review import"   # auto-tags
git push --follow-tags
```
