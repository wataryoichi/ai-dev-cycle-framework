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
