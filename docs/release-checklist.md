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
- [ ] `--max-fix-rounds 1` limits fix rounds correctly
- [ ] Stable detection triggers when findings reach 0
- [ ] No-progress detection triggers on same findings after fix
- [ ] Rollback works
- [ ] `devcycle status` shows correct state
- [ ] Prompt artifacts saved (claude-prompt.txt, codex-prompt.txt, claude-fix-prompt.txt)

## Artifacts

- [ ] fix_plan.json generated when findings exist
- [ ] findings_diff.json generated on fix rounds
- [ ] run_summary.json/md generated for multi-cycle
- [ ] request.json includes spec fields
- [ ] implementation_summary.json generated
- [ ] final-summary.md auto-generated (not left as placeholder)
- [ ] README.md generated at project root

## Stopped Reasons

- [ ] `blocked` — human input needed
- [ ] `completed` — cycle finished
- [ ] `stable` — no findings after fix round
- [ ] `max_cycles_reached` — N cycles done
- [ ] `max_fix_rounds_reached` — fix limit hit
- [ ] `no_progress` — same findings after fix+rereview

## GitHub Integration

- [ ] `--github` flag creates repo via `gh repo create`
- [ ] README.md is present before push (for GitHub display)
- [ ] Cycle folder names are ASCII-only (no unicode path issues)
