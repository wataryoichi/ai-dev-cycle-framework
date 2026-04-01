# devcycle Repositioning: AI CI / Batch Orchestrator

## Decision

`devcycle` is repositioned as a **headless AI CI/batch orchestrator**, not an interactive development tool.

**Claude Code handles the front line — interactive, high-quality, human-in-the-loop development.**
**devcycle handles the back line — unattended execution, audit trails, repeatable review/fix workflows.**

## When to use devcycle

- Nightly/scheduled code review across repos
- PR-level automated review + fix cycles
- Batch processing multiple projects unattended
- Audit trail and compliance evidence generation
- Standardized review/fix/rereview workflows

## When NOT to use devcycle

- Daily interactive development (use Claude Code + Codex plugin instead)
- One-off creative coding sessions
- Rapid prototyping where human feedback is critical
- Any workflow where "the best quality right now" matters more than "repeatable process"

## Core value proposition

> Headless multi-cycle review/fix runner with audit trail.
> AI code review and fix orchestration for unattended workflows.

## Assets that align with this direction

- spec-driven execution
- run_summary.json / .md
- prompt artifacts (claude-prompt.txt, codex-prompt.txt)
- stopped_reason (stable, no_progress, max_fix_rounds, blocked)
- findings_diff.json
- rollback / history
- multi-cycle chaining with carry-forward
- Codex auto-review integration
- locale-aware outputs (en/ja)
- machine-readable JSON + human-readable Markdown dual output

## Roadmap priorities

### High
- GitHub Actions integration
- PR/branch targeting
- Machine-readable exit status contract
- Retry / timeout hardening

### Medium
- Summary HTML dashboard
- Notifications (Slack / GitHub comment)
- Repository fleet mode (multi-repo batch)
- Scheduled runs with per-repo config

### De-emphasized
- Interactive guided mode polish
- Daily-driver UX improvements
- Claude Code feature competition
