# CLAUDE.md

## Post-implementation rules

After any code changes to `dev_cycle/`:

1. **Reinstall**: `pip install -e . --break-system-packages`
2. **Run tests**: `python3 -m pytest tests/ --tb=short`
3. **Smoke test**: `devcycle --version && devcycle doctor`

## Git workflow

- Work on feature branches, not main
- Commit with descriptive messages
- Push and create PR via `gh pr create`
- Squash merge PRs: `gh pr merge N --squash --delete-branch`
- After merge: `git checkout main && git pull`

## Version tagging

- Commit messages starting with `vX.Y.Z` auto-create git tags (post-commit hook)
- Use `devcycle turbo --title "..."` for auto version/commit/tag/push

## Key commands

```bash
devcycle turbo --title "..."    # main workflow
devcycle rollback               # undo
devcycle history                # past versions
devcycle doctor                 # check environment
devcycle status                 # current state
```
