# Version History

### v0.1.0 — bootstrap self-hosting flow

- **Cycle:** `v0.1.0_20260331-034536_bootstrap-self-hosting-flow`
- **Started:** 2026-03-31T03:45:36Z
- **Completed:** 2026-03-31T03:47:09Z

Built the complete AI Dev Cycle Framework from an empty directory. The framework
provides CLI tooling, configuration, documentation, and Claude Code integration
for structured development cycles with review tracking.

- Created Python package with 5 modules (cli, config, cycle, review_orchestrator, __init__)
- 9 CLI commands covering the full cycle lifecycle
- 4 Claude Code slash commands
- 3 documentation files (self-hosting, playbook, version history)
- Git auto-tag hook for version management
- Self-application config for the framework itself

- All CLI commands tested end-to-end
- Full cycle flow tested: start → prepare-review → finalize-review → finalize-cycle
- Auto-tag hook verified with version and non-version commits
- Self-application config validated

- No CI/CD integration yet
- No external project onboarding templates
- Codex review triggering is manual (by design for MVP)

- The framework can now manage its own development from day one
- Every future improvement will be tracked as a cycle
- Cycle logs serve as both development records and usage examples

### v0.9.0 — json test

- **Cycle:** `v0.9.0_20260331-091915_json-test`
- **Started:** 2026-03-31T09:19:15Z
- **Completed:** 2026-03-31T09:19:15Z
