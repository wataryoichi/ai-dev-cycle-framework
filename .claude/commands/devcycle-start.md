Start a new development cycle.

Arguments (version and title): $ARGUMENTS

## Steps

1. **Start**:

```bash
devcycle start --version <VERSION> --title "<TITLE>"
```

2. **Fill request.md**: Goal, Context, Scope, Notes.

3. **Investigate** before implementing: read relevant code, identify changes needed.

4. **Implement** the changes.

5. **Update claude-implementation-summary.md**: what was done, decisions, changed files, testing.

6. **Move to review**:

```bash
devcycle prepare
```

**Tip**: `devcycle next` shows the next command at any point.
