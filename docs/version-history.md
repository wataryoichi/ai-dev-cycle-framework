# Version History

### v0.1.0 — Bootstrap
Initial framework: CLI, config, cycle management, auto-tag hook.

### v0.2.0 — Orchestrator
State machine, run/resume/status, choice UI, non-interactive mode.

### v0.3.0 — Turbo Mode
Turbo orchestrator, AI runners, rollback, dual JSON, spec-driven cycles.

### v0.4.0 — Spec Contract
Spec contract formalized. Turbo + Guided unified on spec.

### v0.5.0 — Multi-cycle + i18n
Multi-cycle execution (`--cycles N`). Japanese/English output (`--lang ja`).

### v0.6.0 — Chain + Locale-hardening
Chain summary, carry-forward, locale alias helpers, section detection fixes.

### v0.7.0 — Codex Auto-import
Real Codex review auto-import verified (codex-cli v0.117.0 / gpt-5.4).
Prompt artifacts saved. Carry-forward in Claude prompts.
Orchestrator fixes for non-interactive + COMPLETED state.
DEVCYCLE_CODEX_CMD="codex review" as standard setup. 244 tests.

### v0.8.0 — Auto-fix Loop
Auto-fix: finding → Claude fix → Codex rereview → no-progress detection.
Fix plan (JSON), prompt artifacts, stderr capture.
Stopped reasons: max_fix_rounds, no_progress, runner timeouts.
Release checklist added. 244 tests.

### v0.8.1 — Fix-loop Polish + README + GitHub
- `--max-fix-rounds` CLI option to control fix loop limit.
- `--github` flag: create a GitHub repo and push via `gh` CLI.
- Auto-generate `final-summary.md` from implementation + review findings.
- Auto-generate `README.md` at project root for GitHub presentation.
- No-progress detection moved after Codex rereview (was firing too early).
- Title used as goal fallback so turbo cycles start implementing immediately.
- ASCII-only cycle folder names (hash fallback for non-ASCII titles).
- Findings diff tracking between fix rounds (`findings_diff.json`).
- Stable detection: auto-complete when findings reach zero after fix.
- 244 tests.
