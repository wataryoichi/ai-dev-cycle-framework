# Release Checklist

## Pre-release

- [ ] `devcycle doctor` passes
- [ ] `python3 -m pytest tests/` all pass
- [ ] `devcycle --version` matches pyproject.toml
- [ ] version-history.md updated
- [ ] README examples are current
- [ ] CLAUDE.md is current

## E2E Verification

- [ ] `devcycle turbo --title "test" --no-push` completes
- [ ] `--lang ja` produces Japanese headings
- [ ] `--cycles 2` creates multiple cycles
- [ ] Codex auto-review works (`DEVCYCLE_CODEX_CMD` set)
- [ ] Auto-fix loop executes (Claude + Codex round-trip)
- [ ] Rollback works
- [ ] `devcycle status` shows correct state
- [ ] Prompt artifacts saved (claude-prompt.txt, codex-prompt.txt)

## Artifacts

- [ ] fix_plan.json generated when findings exist
- [ ] run_summary.json/md generated for multi-cycle
- [ ] request.json includes spec fields
- [ ] implementation_summary.json generated

## Stopped Reasons

- [ ] `blocked` — human input needed
- [ ] `completed` — cycle finished
- [ ] `max_cycles_reached` — N cycles done
- [ ] `max_fix_rounds_reached` — fix limit hit
- [ ] `no_progress` — same findings after fix
