"""Orchestration engine — drives a cycle through the state machine.

The engine never touches stdin/stdout directly in its core logic.
All I/O goes through callback functions, making it testable.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .config import Config
from .cycle import (
    _read_meta,
    _write_meta,
    _update_phase,
    check_cycle,
    finalize_cycle,
    git_info,
    start_cycle,
    StrictFinalizeError,
)
from .review_importer import (
    count_findings,
    generate_followup_draft,
    import_review,
)
from .review_orchestrator import finalize_review, prepare_review
from .state_machine import (
    Choice,
    State,
    STATE_TO_PHASE,
    determine_state,
    get_auto_transition,
    get_blocking_reason,
    get_choices,
    get_default_action,
    get_transitions,
)


# Type for callbacks
InputFn = Callable[[str, list[Choice]], Choice | str]
OutputFn = Callable[[str], None]


@dataclass
class RunResult:
    cycle_dir: Path
    state: State
    cycle_id: str = ""
    history: list[dict] = field(default_factory=list)
    interrupted: bool = False
    blocked: bool = False
    blocked_reason: str = ""
    error: str = ""


def run_cycle(
    cfg: Config,
    version: str,
    title: str,
    input_fn: InputFn | None = None,
    output_fn: OutputFn | None = None,
    non_interactive: bool = False,
) -> RunResult:
    """Run a full cycle from start. Returns when completed or interrupted."""
    output = output_fn or _default_output
    cycle_dir = start_cycle(cfg, version, title)
    meta = _read_meta(cycle_dir)
    output(f"Cycle started: {meta['cycle_id']}")

    return _drive(cfg, cycle_dir, input_fn, output, non_interactive)


def resume_cycle(
    cfg: Config,
    cycle_dir: Path,
    input_fn: InputFn | None = None,
    output_fn: OutputFn | None = None,
    non_interactive: bool = False,
) -> RunResult:
    """Resume an interrupted cycle."""
    output = output_fn or _default_output
    meta = _read_meta(cycle_dir)
    state = determine_state(cycle_dir)
    gi = git_info(cfg.project_root)
    history = meta.get("orchestrator_history", [])

    output(f"Resuming: {meta['cycle_id']}")
    output(f"  State:  {state.value}")
    output(f"  Branch: {gi['branch']} ({gi['head_sha']})")
    if history:
        last = history[-1]
        output(f"  Last:   {last.get('mode', last.get('action', '?'))} → {last.get('to', '?')}")

    return _drive(cfg, cycle_dir, input_fn, output, non_interactive)


def get_status(cfg: Config, cycle_dir: Path) -> dict:
    """Get current status without side effects."""
    meta = _read_meta(cycle_dir)
    state = determine_state(cycle_dir)
    quality = check_cycle(cycle_dir)
    findings = count_findings(cycle_dir)
    transitions = get_transitions(state)
    choices = get_choices(state)

    # Progress estimation
    all_states = list(State)
    try:
        idx = all_states.index(state)
    except ValueError:
        idx = 0
    progress = int(idx / max(len(all_states) - 1, 1) * 100)

    gi = git_info(cfg.project_root)

    return {
        "cycle_id": meta["cycle_id"],
        "version": meta.get("version", ""),
        "title": meta.get("title", ""),
        "state": state.value,
        "phase": meta.get("phase", ""),
        "progress_pct": progress,
        "branch": gi["branch"],
        "head_sha": gi["head_sha"],
        "dirty": gi["dirty"],
        "quality": {
            "ready": len(quality["ready"]),
            "placeholder": len(quality["placeholder"]),
            "missing": len(quality["missing"]),
            "can_finalize": quality["can_finalize"],
            "strict_ready": not quality["all_issues"],
        },
        "findings": findings,
        "available_actions": [
            {"description": t.description, "auto": t.auto}
            for t in transitions
        ],
        "choices": [
            {"key": c.key, "label": c.label}
            for c in choices
        ],
        "history": meta.get("orchestrator_history", []),
    }


# ── Internal engine ──────────────────────────────────────────

def _drive(
    cfg: Config,
    cycle_dir: Path,
    input_fn: InputFn | None,
    output: OutputFn,
    non_interactive: bool = False,
) -> RunResult:
    """Drive the state machine loop."""
    meta = _read_meta(cycle_dir)
    result = RunResult(
        cycle_dir=cycle_dir,
        cycle_id=meta["cycle_id"],
        state=determine_state(cycle_dir),
    )
    inp = input_fn or _default_input

    while result.state != State.COMPLETED:
        state = determine_state(cycle_dir)
        result.state = state

        # Try auto transition
        auto = get_auto_transition(state)
        if auto:
            output(f"  → {auto.description}")
            ok = _execute_action(cfg, cycle_dir, state, auto.to_state, None, output)
            if not ok:
                result.error = f"Failed at: {auto.description}"
                break
            _record_transition(cycle_dir, state, auto.to_state, "auto")
            result.history.append({"from": state.value, "to": auto.to_state.value, "mode": "auto"})
            continue

        # Try AI runners at specific states
        if state == State.IMPLEMENTING:
            from .ai_runner import run_claude
            meta = _read_meta(cycle_dir)
            claude_result = run_claude(cycle_dir, meta.get("title", ""))
            if claude_result["success"]:
                output(f"  → Claude implementation complete")
                if claude_result.get("output"):
                    # Write output to implementation summary
                    summary_path = cycle_dir / "claude-implementation-summary.md"
                    summary_path.write_text(
                        f"# Claude Implementation Summary\n\n"
                        f"## What Was Done\n\n{claude_result['output'][:2000]}\n"
                    )
                _record_transition(cycle_dir, state, State.REVIEW_NEEDED, "auto_claude")
                result.history.append({"from": state.value, "action": "auto_claude"})
                continue
            elif not claude_result["blocked"]:
                output(f"  Claude runner failed: {claude_result['reason']}")
            # If blocked or failed, fall through to interactive/non-interactive

        # Non-interactive: use default action or block
        if non_interactive:
            default = get_default_action(state)
            reason = get_blocking_reason(state)

            if default == "exit" or not default:
                output(f"  Blocked at: {state.value}")
                if reason:
                    output(f"  Reason: {reason}")
                output(f"  Resume with: devcycle resume")
                result.blocked = True
                result.blocked_reason = reason
                result.interrupted = True
                break

            # Execute the default action
            choice_obj = None
            for c in get_choices(state):
                if c.action == default:
                    choice_obj = c
                    break
            if choice_obj:
                output(f"  → [auto] {choice_obj.label}")
                ok = _execute_choice(cfg, cycle_dir, state, choice_obj, inp, output)
                if not ok:
                    result.blocked = True
                    result.blocked_reason = f"Default action failed: {default}"
                    result.interrupted = True
                    break
                _record_transition(cycle_dir, state, determine_state(cycle_dir), f"auto:{default}")
                result.history.append({"from": state.value, "action": default, "mode": "non_interactive"})
                continue
            else:
                result.blocked = True
                result.blocked_reason = reason
                result.interrupted = True
                break

        # Interactive: decision point — get choices
        choices = get_choices(state)
        if choices:
            choice = inp(f"State: {state.value}", choices)

            if isinstance(choice, Choice):
                if choice.action == "exit":
                    output("Paused. Resume with: devcycle resume")
                    result.interrupted = True
                    break

                ok = _execute_choice(cfg, cycle_dir, state, choice, inp, output)
                if not ok:
                    result.interrupted = True
                    break
                _record_transition(cycle_dir, state, determine_state(cycle_dir), choice.action)
                result.history.append({"from": state.value, "action": choice.action})
                continue

        # Needs input (review text) — try Codex runner first
        transitions = get_transitions(state)
        for t in transitions:
            if t.needs_input == "review_text":
                # Try auto Codex review
                from .ai_runner import run_codex
                meta = _read_meta(cycle_dir)
                codex_result = run_codex(cycle_dir, meta.get("title", ""))
                if codex_result["success"] and codex_result["review_text"]:
                    output(f"  → Codex review auto-imported")
                    import_review(cycle_dir, codex_result["review_text"])
                    finalize_review(cfg, cycle_dir)
                    _record_transition(cycle_dir, state, State.FOLLOWUP_NEEDED, "auto_codex")
                    result.history.append({"from": state.value, "action": "auto_codex"})
                    break

                if codex_result["blocked"]:
                    output("Codex review needed (DEVCYCLE_CODEX_CMD not set).")
                else:
                    output("Codex review needed.")
                output("  Provide review results to continue.")
                review_text = inp("review_text", [])
                if isinstance(review_text, str) and review_text.strip():
                    import_review(cycle_dir, review_text)
                    finalize_review(cfg, cycle_dir)
                    _record_transition(cycle_dir, state, State.FOLLOWUP_NEEDED, "import_review")
                    result.history.append({"from": state.value, "action": "import_review"})
                else:
                    output("No review text provided. Resume when ready: devcycle resume")
                    result.interrupted = True
                break
        else:
            # No transitions available — stuck
            output(f"No actions available at state: {state.value}")
            result.interrupted = True
            break

        if result.interrupted:
            break

    result.state = determine_state(cycle_dir)
    return result


def _execute_action(
    cfg: Config, cycle_dir: Path,
    from_state: State, to_state: State,
    choice: Choice | None, output: OutputFn,
) -> bool:
    """Execute a state transition action."""
    try:
        if to_state == State.REVIEW_PENDING:
            prepare_review(cfg, cycle_dir)
        elif to_state == State.FOLLOWUP_NEEDED:
            finalize_review(cfg, cycle_dir)
        elif to_state == State.FOLLOWUP_READY:
            draft = generate_followup_draft(cycle_dir)
            if draft:
                (cycle_dir / "codex-followup.md").write_text(draft)
                counts = count_findings(cycle_dir)
                output(f"  Followup draft generated ({counts['total']} findings)")
        return True
    except Exception as e:
        output(f"  Error: {e}")
        return False


def _execute_choice(
    cfg: Config, cycle_dir: Path,
    state: State, choice: Choice,
    inp: InputFn, output: OutputFn,
) -> bool:
    """Execute a user-chosen action."""
    try:
        if choice.action == "prepare_review":
            prepare_review(cfg, cycle_dir)
            output("  Review prepared. Waiting for Codex review input.")
            return True

        elif choice.action == "apply_fixes":
            output("  Apply fixes based on followup decisions.")
            output("  (Edit code, then resume to continue)")
            return True

        elif choice.action == "skip_to_finalize":
            return True

        elif choice.action in ("check_and_finalize", "finalize_strict", "finalize"):
            strict = choice.action == "finalize_strict"
            if choice.action == "check_and_finalize":
                quality = check_cycle(cycle_dir)
                strict = not quality["all_issues"]

            try:
                finalize_cycle(cfg, cycle_dir, strict=strict)
                output("  Cycle finalized.")
            except StrictFinalizeError as e:
                output(f"  Strict finalize failed: {len(e.warnings)} issue(s)")
                for w in e.warnings:
                    output(f"    - {w}")
                return False
            return True

        elif choice.action == "rereview":
            prepare_review(cfg, cycle_dir)
            output("  Re-review prepared. Provide new review results.")
            return True

        return True
    except Exception as e:
        output(f"  Error: {e}")
        return False


def _record_transition(cycle_dir: Path, from_state: State, to_state: State, mode: str) -> None:
    """Record transition in meta.json."""
    meta = _read_meta(cycle_dir)
    meta["orchestrator_state"] = to_state.value
    phase = STATE_TO_PHASE.get(to_state, meta.get("phase", "started"))
    _update_phase(meta, phase)

    history = meta.get("orchestrator_history", [])
    history.append({"from": from_state.value, "to": to_state.value, "mode": mode})
    meta["orchestrator_history"] = history
    _write_meta(cycle_dir, meta)


def _default_output(msg: str) -> None:
    print(msg, file=sys.stderr)


def _default_input(prompt: str, choices: list[Choice]) -> Choice | str:
    """Default interactive input handler."""
    from .choice_ui import prompt_choice, prompt_review_input

    if prompt == "review_text":
        return prompt_review_input()

    if choices:
        return prompt_choice(choices, header=prompt)

    return ""
