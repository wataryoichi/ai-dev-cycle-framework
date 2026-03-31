Start a new development cycle for this project.

## Instructions

1. Run the start-cycle CLI to create a new cycle directory:

```bash
python3 -m dev_cycle.cli start-cycle --version <VERSION> --title "<TITLE>"
```

Ask the user for the version and title if not provided as arguments: $ARGUMENTS

2. Confirm the created cycle directory exists and list its contents.

3. Open `request.md` in the new cycle directory and fill it in:
   - Describe the goal of this cycle
   - Note any constraints, dependencies, or context
   - Reference related issues or prior cycles if applicable

4. Before starting implementation, do a brief investigation:
   - Read relevant existing code
   - Check for related issues or TODOs
   - Note anything that might affect the approach

5. Report the cycle directory path and confirm readiness to begin implementation.
