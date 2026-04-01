# Feature Ideas

## High Priority — CI/Batch Foundation
- [ ] GitHub Actions workflow template (nightly review)
- [ ] PR/branch targeting (`devcycle turbo --branch feat/foo`)
- [ ] Machine-readable exit status contract (documented exit codes)
- [ ] Retry / timeout hardening for runner failures
- [ ] Artifact upload strategy for CI (summary → PR comment or Actions summary)
- [x] ~~Auto-fix loop~~ (done in v0.8.0)
- [x] ~~`--github` flag for repo creation~~ (done in v0.8.1)
- [x] ~~`--continue-from` for iterating on previous cycles~~ (done in v0.8.1)
- [x] ~~`export` command~~ (done in v0.8.1)
- [x] ~~Auto README.md generation~~ (done in v0.8.1)
- [x] ~~Stable / no-progress detection~~ (done in v0.8.1)

## Medium Priority — Observability & Notifications
- [ ] Summary HTML dashboard (single-page report from run_summary)
- [ ] GitHub PR comment with findings summary
- [ ] Slack / webhook notification on completion
- [ ] `devcycle report` — generate human-readable report from artifacts

## Medium Priority — Multi-Repo / Fleet
- [ ] Repository fleet mode (`devcycle batch --repos repos.txt`)
- [ ] Per-repo config overrides
- [ ] Scheduled runs with cron-style config
- [ ] Parallel execution across repos

## Lower Priority
- [ ] PyPI publish
- [ ] `devcycle diff --from v1 --to v2` (version comparison)
- [x] ~~Dual JSON files alongside Markdown~~ (done in v0.3.0)
- [x] ~~Multi-cycle execution~~ (done in v0.5.0)

## De-emphasized
- Interactive guided mode polish
- GUI / TUI dashboard
- Claude Code feature competition
- "Daily driver" UX improvements
