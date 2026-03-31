Run a full development cycle from start to finish.

Arguments (version, title, and goal): $ARGUMENTS

---

## Phase 1 — Start

```bash
devcycle start --version <VERSION> --title "<TITLE>"
```

Fill in `request.md`: Goal, Context, Scope, Notes.

## Phase 2 — Implement

Make the code changes. Update `claude-implementation-summary.md`.

## Phase 3 — Prepare

```bash
devcycle prepare
```

Prints a copy-paste Codex prompt and import options.

## Phase 4 — Codex Review (HUMAN)

Run Codex review. Save output to `codex-output.txt`.

## Phase 5 — Import Review

```bash
cat codex-output.txt | devcycle review-loop --generate-followup
```

## Phase 6 — Address Findings

Edit `codex-followup.md`: accept/defer/reject each finding. Implement fixes.

## Phase 7 — Re-review?

```bash
devcycle next
```

| Hint | Action |
|------|--------|
| `recommended` | `devcycle prepare` → back to Phase 3 |
| `optional` | Your judgment |
| `not_needed` | Proceed to finalize |

## Phase 8 — Check + Finalize

```bash
devcycle check
devcycle finalize --strict
```

---

| # | Phase | Command | Who |
|---|-------|---------|-----|
| 1 | Start | `devcycle start` | Claude |
| 2 | Implement | (code + summary) | Claude |
| 3 | Prepare | `devcycle prepare` | CLI |
| 4 | Review | Run Codex | HUMAN |
| 5 | Import | `devcycle review-loop` | CLI |
| 6 | Follow-up | `devcycle followup` + fix | Claude |
| 7 | Re-review? | `devcycle next` | CLI |
| 8 | Finalize | `devcycle check` + `devcycle finalize` | CLI |

**Lost?** `devcycle next`
