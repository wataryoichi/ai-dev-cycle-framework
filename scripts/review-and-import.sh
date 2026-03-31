#!/usr/bin/env bash
#
# review-and-import.sh — run Codex review and import in one step.
#
# Usage:
#   ./scripts/review-and-import.sh codex-output.txt
#   cat codex-output.txt | ./scripts/review-and-import.sh
#
# What it does:
#   1. Reads review output from file arg or stdin
#   2. Pipes to run-review-loop --generate-followup
#   3. Shows next-step
#
# This is a convenience wrapper. You can also run the commands directly:
#   cat codex-output.txt | python3 -m dev_cycle.cli run-review-loop --generate-followup

set -euo pipefail

if [ $# -ge 1 ] && [ -f "$1" ]; then
    # File argument
    python3 -m dev_cycle.cli run-review-loop --from-file "$1" --generate-followup
else
    # stdin
    python3 -m dev_cycle.cli run-review-loop --generate-followup
fi

echo ""
echo "--- Current status ---"
python3 -m dev_cycle.cli next-step
