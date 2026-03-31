Finalize the current development cycle.

Arguments (optional cycle dir): $ARGUMENTS

## Pre-check

```bash
devcycle check
```

## Checklist

- [ ] `claude-implementation-summary.md` filled
- [ ] `codex-review.md` has findings (or review skipped)
- [ ] `codex-followup.md` documents decisions
- [ ] `final-summary.md` written (Overview, Changes, Verification, Remaining Issues)

## Finalize

```bash
devcycle finalize          # warns but proceeds
devcycle finalize --strict # fails if any file unfilled
```

Use `--strict` for releases and core logic changes.
