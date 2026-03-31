# AI Dev Cycle Framework

Claude→Codex→Claude orchestrator. Runs development cycles with automatic
phase progression and interactive prompts at decision points.

## Install

```bash
pip install -e .
devcycle doctor            # check environment, branch, hooks
source <(devcycle completion bash)  # optional: shell completion
```

## Usage

```bash
git checkout -b feat/my-feature   # work on a branch
devcycle run --version v0.1.0 --title "add user auth"
```

This runs the full cycle:
1. Creates cycle directory with templates
2. Pauses for implementation (you write code + fill summary)
3. Prepares review and shows Codex prompt
4. Pauses for Codex review input
5. Imports review, generates followup draft
6. Pauses for fix decisions
7. Checks quality and finalizes

At each pause, you choose what to do (numbered choices). To continue later:

```bash
devcycle resume
```

To see where you are:

```bash
devcycle status
```

## Shell Completion

```bash
source <(devcycle completion bash)   # bash
source <(devcycle completion zsh)    # zsh
```

## Commands

### Primary

| Command | Description |
|---------|-------------|
| `run` | Run a full cycle with interactive prompts |
| `resume` | Continue an interrupted cycle |
| `status` | Show state, progress, and available actions |
| `doctor` | Check environment setup |

### Manual Mode (Advanced)

For step-by-step control:

| Command | Description |
|---------|-------------|
| `start` | Start a new cycle |
| `prepare` | Prepare for Codex review |
| `review-loop` | Import review (prepare + import + finalize) |
| `followup` | Generate follow-up draft from findings |
| `next` | Show next command to run |
| `check` | Quality report |
| `finalize` | Complete cycle (`--strict`) |
| `handoff` | Show Codex prompt (no phase change) |
| `import-review` | Import review output |
| `index` | List cycles |
| `latest` | Latest cycle path |

All commands support `--json`.

## How It Works

### States

The orchestrator tracks these states:

| State | What happens |
|-------|-------------|
| `started` | Fill request.md |
| `implementing` | Write code, fill implementation summary |
| `review_needed` | Auto: prepares review |
| `review_pending` | You provide Codex review output |
| `followup_needed` | Auto: generates followup draft |
| `followup_ready` | You decide: accept/defer/reject findings |
| `fix_needed` | Apply fixes |
| `ready_to_finalize` | Choose: strict finalize, normal, or re-review |
| `completed` | Done |

States marked "Auto" execute without prompting. Others present numbered choices.

### Decision Points

At each decision point, you see something like:

```
Choose next action:
  1. Implementation is done, proceed to review
  2. Not done yet, exit (resume later)
```

### `followup` — What It Generates

Reads `codex-review.md`, writes `codex-followup.md`:

```markdown
## Accepted
- [HIGH] finding: <!-- action taken -->
- [MEDIUM] finding: <!-- action taken -->

## Deferred
## Rejected
```

This is a draft. Move items to Deferred/Rejected as needed.

## Dual Output

Each cycle produces both Markdown (human-readable) and JSON (machine-readable):

```
ops/dev-cycles/<cycle_id>/
  meta.json                          # state, timestamps, orchestrator history
  request.md                         # what was requested
  claude-implementation-summary.md   # what was implemented
  codex-review.md                    # review findings
  codex-followup.md                  # accept/defer/reject decisions
  final-summary.md                   # cycle summary
```

`meta.json` contains all structured data including orchestrator state and transition history.

## Pipe / CI / Hook

```bash
# stdin pipe for review import
cat codex-output.txt | devcycle review-loop --generate-followup

# CI samples included
.github/workflows/devcycle-check.yml     # PR quality gate
.github/workflows/devcycle-finalize.yml  # merge finalize

# Review hook
export DEVCYCLE_CODEX_CMD="codex review --prompt"
cp scripts/hooks/post-prepare-review.sample scripts/hooks/post-prepare-review
```

## Self-Hosting

This project uses its own tooling. See [docs/self-hosting.md](docs/self-hosting.md).

## License

MIT
