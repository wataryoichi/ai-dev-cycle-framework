"""State machine for cycle orchestration.

Determines current state from cycle directory content and defines
transitions with auto-executability flags and choice points.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class State(str, Enum):
    """Cycle states — superset of PHASES, with decision points."""
    STARTED = "started"
    IMPLEMENTING = "implementing"
    REVIEW_NEEDED = "review_needed"
    REVIEW_PENDING = "review_pending"       # waiting for external review input
    REVIEW_IMPORTED = "review_imported"
    FOLLOWUP_NEEDED = "followup_needed"
    FOLLOWUP_READY = "followup_ready"       # draft generated, user decides
    FIX_NEEDED = "fix_needed"
    READY_TO_FINALIZE = "ready_to_finalize"
    COMPLETED = "completed"


# Map state machine states to canonical PHASES stored in meta.json
STATE_TO_PHASE = {
    State.STARTED: "started",
    State.IMPLEMENTING: "started",
    State.REVIEW_NEEDED: "implementation_done",
    State.REVIEW_PENDING: "review_pending",
    State.REVIEW_IMPORTED: "review_imported",
    State.FOLLOWUP_NEEDED: "review_done",
    State.FOLLOWUP_READY: "review_done",
    State.FIX_NEEDED: "review_done",
    State.READY_TO_FINALIZE: "followup_done",
    State.COMPLETED: "completed",
}


@dataclass
class Choice:
    key: int
    label: str
    action: str        # action function name in orchestrator


@dataclass
class Transition:
    from_state: State
    to_state: State
    description: str
    auto: bool = False              # can execute without user input
    needs_input: str | None = None  # e.g. "review_text"
    choices: list[Choice] = field(default_factory=list)
    default_action: str = ""        # action to take in non-interactive mode
    blocking_reason: str = ""       # why non-interactive can't proceed


def determine_state(cycle_dir: Path) -> State:
    """Determine the actual state by inspecting cycle directory content."""
    from .cycle import _read_meta, _is_placeholder, check_cycle

    meta_path = cycle_dir / "meta.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"No meta.json in {cycle_dir}")

    meta = _read_meta(cycle_dir)

    # Check orchestrator state first (if set by run/resume)
    orch_state = meta.get("orchestrator_state")
    if orch_state and orch_state in State.__members__.values():
        # Validate it still makes sense
        pass  # fall through to content-based checks for accuracy

    phase = meta.get("phase", meta.get("status", "started"))

    if phase == "completed":
        return State.COMPLETED

    # Content-based determination
    impl_filled = not _is_placeholder(cycle_dir / "claude-implementation-summary.md")
    review_filled = not _is_placeholder(cycle_dir / "codex-review.md")
    followup_filled = not _is_placeholder(cycle_dir / "codex-followup.md")
    summary_filled = not _is_placeholder(cycle_dir / "final-summary.md")

    if summary_filled and impl_filled:
        quality = check_cycle(cycle_dir)
        if not quality["all_issues"]:
            return State.READY_TO_FINALIZE
        return State.FIX_NEEDED

    if followup_filled and review_filled:
        return State.FIX_NEEDED

    if review_filled and not followup_filled:
        # Review imported but followup not done yet
        from .review_importer import count_findings
        counts = count_findings(cycle_dir)
        if counts["total"] > 0:
            return State.FOLLOWUP_NEEDED
        return State.READY_TO_FINALIZE

    if phase in ("review_pending", "review_imported"):
        if review_filled:
            return State.FOLLOWUP_NEEDED
        return State.REVIEW_PENDING

    if impl_filled:
        return State.REVIEW_NEEDED

    if phase == "started":
        # request.md always has version/title from template, so check for Goal content
        req = cycle_dir / "request.md"
        req_has_goal = False
        if req.exists():
            content = req.read_text()
            # Check for goal section in any language, without placeholder comments
            has_goal_header = ("## Goal" in content or "## 目的" in content)
            has_placeholder = ("<!-- Describe" in content or "<!-- 目的を記述" in content)
            req_has_goal = has_goal_header and not has_placeholder
        if req_has_goal:
            return State.IMPLEMENTING
        return State.STARTED

    return State.STARTED


def get_transitions(state: State) -> list[Transition]:
    """Return available transitions from a given state."""
    return _TRANSITIONS.get(state, [])


def get_auto_transition(state: State) -> Transition | None:
    """Return the auto-executable transition if one exists."""
    for t in get_transitions(state):
        if t.auto:
            return t
    return None


def get_choices(state: State) -> list[Choice]:
    """Return choices available at a decision point."""
    for t in get_transitions(state):
        if t.choices:
            return t.choices
    return []


def get_default_action(state: State) -> str:
    """Return the default action for non-interactive mode."""
    for t in get_transitions(state):
        if t.default_action:
            return t.default_action
    return "exit"


def get_blocking_reason(state: State) -> str:
    """Return why non-interactive can't proceed at this state."""
    for t in get_transitions(state):
        if t.blocking_reason:
            return t.blocking_reason
    return ""


# ── Transition definitions ───────────────────────────────────

_TRANSITIONS: dict[State, list[Transition]] = {
    State.STARTED: [
        Transition(
            State.STARTED, State.IMPLEMENTING,
            "Fill request.md and begin implementation",
            blocking_reason="Implementation has not started",
        ),
    ],
    State.IMPLEMENTING: [
        Transition(
            State.IMPLEMENTING, State.REVIEW_NEEDED,
            "Implementation done — prepare for review",
            choices=[
                Choice(1, "Done implementing — move to review", "prepare_review"),
                Choice(2, "Need more time — exit and resume later", "exit"),
            ],
            default_action="exit",
            blocking_reason="Implementation in progress — fill summary and resume",
        ),
    ],
    State.REVIEW_NEEDED: [
        Transition(
            State.REVIEW_NEEDED, State.REVIEW_PENDING,
            "Prepare review and hand off to Codex",
            auto=True,
        ),
    ],
    State.REVIEW_PENDING: [
        Transition(
            State.REVIEW_PENDING, State.FOLLOWUP_NEEDED,
            "Import Codex review results",
            needs_input="review_text",
            blocking_reason="Codex review input required",
        ),
    ],
    State.REVIEW_IMPORTED: [
        Transition(
            State.REVIEW_IMPORTED, State.FOLLOWUP_NEEDED,
            "Finalize review and generate followup",
            auto=True,
        ),
    ],
    State.FOLLOWUP_NEEDED: [
        Transition(
            State.FOLLOWUP_NEEDED, State.FOLLOWUP_READY,
            "Generate followup draft",
            auto=True,
        ),
    ],
    State.FOLLOWUP_READY: [
        Transition(
            State.FOLLOWUP_READY, State.FIX_NEEDED,
            "Review followup and apply fixes",
            choices=[
                Choice(1, "Apply fixes based on followup", "apply_fixes"),
                Choice(2, "Edit followup first — exit and resume later", "exit"),
                Choice(3, "No fixes needed — finalize now", "skip_to_finalize"),
            ],
            default_action="exit",
            blocking_reason="Followup review and fix decisions needed",
        ),
    ],
    State.FIX_NEEDED: [
        Transition(
            State.FIX_NEEDED, State.READY_TO_FINALIZE,
            "Check quality and prepare to finalize",
            choices=[
                Choice(1, "Fixes done — check quality and finalize", "check_and_finalize"),
                Choice(2, "Request another Codex review", "rereview"),
                Choice(3, "Still fixing — exit and resume later", "exit"),
            ],
            default_action="exit",
            blocking_reason="Fixes in progress — implement fixes and resume",
        ),
    ],
    State.READY_TO_FINALIZE: [
        Transition(
            State.READY_TO_FINALIZE, State.COMPLETED,
            "Finalize the cycle",
            choices=[
                Choice(1, "Finalize with strict quality check", "finalize_strict"),
                Choice(2, "Finalize (allow warnings)", "finalize"),
                Choice(3, "Request another Codex review first", "rereview"),
            ],
            default_action="finalize",
            blocking_reason="",
        ),
    ],
}
