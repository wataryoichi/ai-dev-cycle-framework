Process Codex review feedback: judge → fix → record → decide re-review.

Arguments (optional cycle dir): $ARGUMENTS

## Step 1 — Status

```bash
devcycle next
```

## Step 2 — Generate followup draft

```bash
devcycle followup
```

## Step 3 — Judge each finding

Edit `codex-followup.md`:

- **Accept**: `- [HIGH] Finding: added validation in foo.py:L45`
- **Defer**: `- [MEDIUM] Finding: needs separate cycle`
- **Reject**: `- [LOW] Finding: already handled by X`

## Step 4 — Implement fixes

## Step 5 — Update records

- `claude-implementation-summary.md` if implementation changed
- `final-summary.md`: Overview, Changes, Verification, Remaining Issues

## Step 6 — Re-review?

```bash
devcycle next
```

| Hint | Action |
|------|--------|
| `recommended` | `devcycle prepare` |
| `optional` | Your judgment |
| `not_needed` | `devcycle finalize` |

## Step 7 — Finalize

```bash
devcycle check
devcycle finalize --strict
```
