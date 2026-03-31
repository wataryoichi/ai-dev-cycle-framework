# Feature Ideas

Future improvements and directions for ai-dev-cycle-framework.

## Near-term

- [ ] Codex stdout pipe: `codex ... | devcycle review-loop --generate-followup`
- [ ] `turbo` with inline Claude implementation prompts
- [ ] `turbo --watch` — auto-cycle on file changes
- [ ] `rollback --dry-run` — preview what would change
- [ ] `stable` tag concept — mark known-good versions
- [ ] Auto-generated CHANGELOG.md from turbo history
- [ ] `devcycle diff --from v1 --to v2` — compare versions

## Medium-term

- [ ] `--non-interactive` mode for `run` / `resume` (CI use)
- [ ] Claude Code hook: auto-trigger review after implementation
- [ ] Dashboard / TUI for cycle status
- [ ] PyPI publish: `pip install ai-dev-cycle-framework`
- [ ] Multi-project support from single CLI
- [ ] `devcycle init` — bootstrap a new project with config

## Longer-term

- [ ] Full Claude↔Codex loop without human intervention
- [ ] Web UI for cycle management
- [ ] Team features: shared cycle index, review assignment
- [ ] Integration with Linear, GitHub Issues, Jira
- [ ] Metrics: cycle time, review findings trend, rollback frequency
