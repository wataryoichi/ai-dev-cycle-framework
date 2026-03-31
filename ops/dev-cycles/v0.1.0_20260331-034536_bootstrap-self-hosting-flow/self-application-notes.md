# Self-Application Notes

## Change Type
Internal tooling + user-facing feature (bootstrap — everything is new)

## Impact on Framework Development
- Establishes the foundation: from this point, framework improvements are tracked as cycles
- The cycle directory itself serves as a usage example for new adopters
- `next-step` eliminates the "what do I do next?" problem during framework development
- `run-review-loop --generate-followup` makes the review-to-fix handoff fast
- `review-handoff` gives quick Codex prompt access without changing phase (useful during re-review)
- `check-cycle` and `--strict` prevent incomplete cycles from being finalized
- JSON output on `next-step`, `check-cycle`, `review-handoff` enables future CI automation
