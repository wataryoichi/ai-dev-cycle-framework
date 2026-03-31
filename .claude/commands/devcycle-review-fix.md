Review and address Codex review feedback for the current cycle.

## Instructions

1. Find the current cycle directory. If not provided as an argument, use:

```bash
python3 -m dev_cycle.cli latest-cycle
```

Arguments (optional cycle dir): $ARGUMENTS

2. Read `codex-review.md` in the cycle directory.

3. For each review item, decide:
   - **Accept**: The feedback is valid — implement the fix
   - **Defer**: Valid but out of scope for this cycle — note for follow-up
   - **Reject**: The feedback is incorrect or not applicable — explain why

4. Implement all accepted fixes.

5. Update `codex-followup.md` with:

```markdown
## Accepted
- [item]: [what was changed]

## Deferred
- [item]: [reason for deferral]

## Rejected
- [item]: [reason for rejection]
```

6. Update `claude-implementation-summary.md` if the fixes changed the implementation
   significantly.

7. Report what was changed and what remains.
