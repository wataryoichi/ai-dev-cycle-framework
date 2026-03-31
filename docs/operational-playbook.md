# Operational Playbook

Day-to-day rules for running development cycles on this project.

## When to Create a Cycle

**Always create a cycle for:**
- New features or commands
- Bug fixes that touch multiple files
- Architectural changes
- Documentation overhauls

**Skip the cycle for:**
- Typo fixes in docs (single file, obvious change)
- Dependency version bumps with no code changes
- `.gitignore` or editor config changes

## Cycle Granularity

One cycle = one coherent unit of work. Guidelines:

- If you can describe the change in a single sentence, it's one cycle.
- If the work spans multiple unrelated areas, split into separate cycles.
- If unsure, start one cycle and split later if it grows too large.

## Version Numbering

Follow semver for version labels:

- `v0.x.y` — pre-1.0 development (current phase)
- Bump patch (`y`) for fixes and small additions
- Bump minor (`x`) for new features or commands
- Bump major only at significant milestones

Multiple cycles can share the same version. The version label groups related work.

## Light Changes

For small, well-scoped changes:

1. `start-cycle` with a descriptive title
2. Implement
3. Write a brief `claude-implementation-summary.md`
4. Skip Codex review (optional for small changes)
5. `finalize-cycle`

## Large Changes

For significant features or refactors:

1. `start-cycle`
2. Fill `request.md` with full context
3. Implement
4. Write thorough `claude-implementation-summary.md`
5. Run Codex review — save to `codex-review.md`
6. Process feedback via `/devcycle-review-fix`
7. `finalize-cycle`

## When to Use Adversarial Review

Use adversarial review (asking Codex to try to break or find flaws) when:

- The change affects core cycle logic (config loading, index management)
- Security-sensitive changes (if/when auth or external integrations are added)
- Changes to CLI argument parsing or file format handling

## When to Use Rescue

Use the rescue flow (delegating to Codex for a second implementation pass) when:

- Claude's implementation has failed twice on the same issue
- The root cause is unclear after investigation
- A fundamentally different approach might be needed

## History Updates

**Mandatory** history update (via `finalize-cycle`) for:
- All completed cycles
- Version milestone announcements

**Optional** manual history entries for:
- Project status summaries
- Migration notes

## Review Checklist

Before finalizing any cycle, verify:

- [ ] `final-summary.md` accurately describes the changes
- [ ] Changed files are listed
- [ ] No temporary or debug code left behind
- [ ] Tests pass (when applicable)
- [ ] Documentation updated if behavior changed
- [ ] `self-application-notes.md` filled in if the framework itself was modified
