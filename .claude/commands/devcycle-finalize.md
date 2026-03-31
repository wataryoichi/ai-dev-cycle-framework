Finalize the current development cycle.

## Instructions

1. Find the current cycle directory. If not provided as an argument, use:

```bash
python3 -m dev_cycle.cli latest-cycle
```

Arguments (optional cycle dir): $ARGUMENTS

2. Update `final-summary.md` in the cycle directory with:
   - A concise summary of what was implemented
   - List of changed files
   - Verification steps taken or recommended
   - Remaining issues or follow-up items

3. If this is a self-application cycle (changes to the framework itself), add a
   `## Self-Application Impact` section describing how this improves the framework's
   own development workflow.

4. Run the finalize-cycle CLI:

```bash
python3 -m dev_cycle.cli finalize-cycle --cycle-dir <CYCLE_DIR>
```

5. Verify that:
   - `meta.json` status is now `completed`
   - `index.jsonl` has a new entry
   - `docs/version-history.md` has been updated

6. Report completion with a brief summary of the cycle.
