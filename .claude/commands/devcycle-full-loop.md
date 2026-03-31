Run a full development cycle from start to finish.

This command guides through the complete cycle. Not all steps are fully automated —
some require human or external input (e.g., Codex review).

## Arguments

$ARGUMENTS

## Standard Flow

### Step 1 — Start Cycle
Run `/devcycle-start` with the version and title for this cycle.

### Step 2 — Fill request.md
Document the goal, context, and constraints in the cycle's `request.md`.

### Step 3 — Implement
Carry out the implementation work described in the request.

### Step 4 — Update claude-implementation-summary.md
Write a summary of what was implemented, key decisions, and any trade-offs.

### Step 5 — Codex Review
Pause and instruct the user to run Codex review. Suggest:

```
Review the changes in this cycle. Focus on correctness, edge cases, and maintainability.
Write your findings to <cycle_dir>/codex-review.md.
```

### Step 6 — Address Review Feedback
Run `/devcycle-review-fix` to process the Codex review results.

### Step 7 — Finalize
Run `/devcycle-finalize` to complete the cycle, update the index, and append
to version history.

### Step 8 — Verify
Confirm all cycle artifacts are in place:
- meta.json (status: completed)
- request.md
- claude-implementation-summary.md
- codex-review.md
- codex-followup.md
- final-summary.md
- index.jsonl updated
- version-history.md updated
