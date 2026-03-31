"""CLI entry point for the dev cycle framework."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import Config
from .cycle import (
    PHASES,
    NoCyclesError,
    StrictFinalizeError,
    _resolve_cycle_dir,
    _read_meta,
    _update_phase,
    _write_meta,
    check_cycle,
    find_latest_cycle,
    finalize_cycle,
    load_index,
    next_step,
    start_cycle,
)
from .review_importer import (
    count_findings,
    generate_followup_draft,
    import_review,
    read_input,
)
from .review_orchestrator import finalize_review, prepare_review


def _resolve_dir(cfg: Config, cycle_dir_arg: str | None) -> Path:
    try:
        return _resolve_cycle_dir(cfg, cycle_dir_arg)
    except NoCyclesError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)


# ── start-cycle ──────────────────────────────────────────────

def cmd_start_cycle(args: argparse.Namespace) -> None:
    cfg = Config.load(Path(args.project_root))
    cycle_dir = start_cycle(cfg, args.version, args.title)
    meta = _read_meta(cycle_dir)

    if getattr(args, "json", False):
        print(json.dumps({
            "cycle_id": meta["cycle_id"],
            "version": meta["version"],
            "title": meta["title"],
            "phase": meta["phase"],
            "cycle_dir": str(cycle_dir),
            "started_at": meta["started_at"],
        }, indent=2))
        return

    print(f"Cycle started: {cycle_dir}")
    print()
    print("Next steps:")
    print(f"  1. Edit {cycle_dir}/request.md — describe the goal")
    print(f"  2. Implement the changes")
    print(f"  3. Update {cycle_dir}/claude-implementation-summary.md")
    print(f"  4. Run: python3 -m dev_cycle.cli prepare-review")


# ── prepare-review ───────────────────────────────────────────

def cmd_prepare_review(args: argparse.Namespace) -> None:
    cfg = Config.load(Path(args.project_root))
    cycle_dir = _resolve_dir(cfg, args.cycle_dir)
    info = prepare_review(cfg, cycle_dir)
    prompt = (
        f"Review the changes for: {info['title']}. "
        f"Focus on correctness, edge cases, and maintainability. "
        f"Structure findings as High / Medium / Low severity."
    )
    import_cmd = "python3 -m dev_cycle.cli run-review-loop --from-file codex-output.txt --generate-followup"
    pipe_cmd = "cat codex-output.txt | python3 -m dev_cycle.cli run-review-loop --generate-followup"

    if args.json:
        print(json.dumps({
            "cycle_id": info["cycle_id"],
            "version": info["version"],
            "title": info["title"],
            "branch": info["branch"],
            "phase": info["phase"],
            "prompt": prompt,
            "import_command": import_cmd,
            "pipe_command": pipe_cmd,
        }, indent=2))
        return

    print(f"Review prepared: {info['cycle_id']}")
    print(f"  Version: {info['version']}")
    print(f"  Title:   {info['title']}")
    print(f"  Branch:  {info['branch']}")
    print()
    print("┌─ Codex review prompt (copy-paste) ─────────────────────┐")
    print(f"│ {prompt}")
    print("└────────────────────────────────────────────────────────┘")
    print()
    # Check for review hook
    import os
    hook_path = Path(args.project_root).resolve() / "scripts" / "hooks" / "post-prepare-review"
    codex_env = os.environ.get("DEVCYCLE_CODEX_CMD", "")
    if hook_path.exists() and codex_env:
        print("Review hook detected (DEVCYCLE_CODEX_CMD is set).")
        print(f"  Automatic review will run via: {hook_path}")
        print()
    elif hook_path.exists():
        print("Review hook installed but DEVCYCLE_CODEX_CMD not set (dry-run mode).")
        print(f"  Set: export DEVCYCLE_CODEX_CMD='codex review --prompt'")
        print()

    print("After review, import results (pick one):")
    print()
    print(f"  # Recommended — all-in-one:")
    print(f"  {import_cmd}")
    print()
    print(f"  # Or pipe:")
    print(f"  {pipe_cmd}")
    print()
    print(f"  # Or step by step:")
    print(f"  python3 -m dev_cycle.cli import-review --from-file codex-output.txt")
    print(f"  python3 -m dev_cycle.cli finalize-review")
    if info["recent_commits"]:
        print()
        print("Recent commits:")
        for line in info["recent_commits"].split("\n")[:5]:
            print(f"  {line}")


# ── review-handoff ───────────────────────────────────────────

def cmd_review_handoff(args: argparse.Namespace) -> None:
    cfg = Config.load(Path(args.project_root))
    cycle_dir = _resolve_dir(cfg, args.cycle_dir)
    meta = _read_meta(cycle_dir)
    from .cycle import _run_git
    branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cfg.project_root) or "unknown"
    counts = count_findings(cycle_dir)
    prompt = (
        f"Review the changes for: {meta['title']}. "
        f"Focus on correctness, edge cases, and maintainability. "
        f"Structure findings as High / Medium / Low severity."
    )
    import_cmd = "python3 -m dev_cycle.cli run-review-loop --from-file codex-output.txt --generate-followup"
    pipe_cmd = "cat codex-output.txt | python3 -m dev_cycle.cli run-review-loop --generate-followup"

    if args.json:
        print(json.dumps({
            "cycle_id": meta["cycle_id"],
            "title": meta["title"],
            "branch": branch,
            "phase": meta.get("phase", "?"),
            "findings": counts,
            "prompt": prompt,
            "import_command": import_cmd,
            "pipe_command": pipe_cmd,
        }, indent=2))
        return

    print(f"Cycle:  {meta['cycle_id']}")
    print(f"Title:  {meta['title']}")
    print(f"Branch: {branch}")
    print(f"Phase:  {meta.get('phase', '?')}")
    if counts["total"] > 0:
        print(f"Prior findings: {counts['high']} high, {counts['medium']} medium, {counts['low']} low")
    print()
    print("Codex review prompt:")
    print(f"  {prompt}")
    print()
    print("Import:")
    print(f"  $ {import_cmd}")
    print(f"  $ {pipe_cmd}")
    print()
    print("Then: $ python3 -m dev_cycle.cli generate-followup")
    print("Then: $ python3 -m dev_cycle.cli check-cycle")


# ── import-review ────────────────────────────────────────────

def cmd_import_review(args: argparse.Namespace) -> None:
    cfg = Config.load(Path(args.project_root))
    cycle_dir = _resolve_dir(cfg, args.cycle_dir)
    raw_text = read_input(args.from_file, args.text)
    review_path = import_review(cycle_dir, raw_text)
    counts = count_findings(cycle_dir)
    meta = _read_meta(cycle_dir)

    if getattr(args, "json", False):
        print(json.dumps({
            "cycle_id": meta["cycle_id"],
            "phase": meta.get("phase", "?"),
            "review_file": str(review_path),
            "findings": counts,
        }, indent=2))
        return

    print(f"Review imported: {review_path}")
    print(f"  Findings: {counts['high']} high, {counts['medium']} medium, {counts['low']} low")
    print()
    print("Next: python3 -m dev_cycle.cli finalize-review")


# ── finalize-review ──────────────────────────────────────────

def cmd_finalize_review(args: argparse.Namespace) -> None:
    cfg = Config.load(Path(args.project_root))
    cycle_dir = _resolve_dir(cfg, args.cycle_dir)
    warnings = finalize_review(cfg, cycle_dir)

    if warnings:
        print("Warnings:")
        for w in warnings:
            print(f"  - {w}")
        print()

    print(f"Review finalized: {cycle_dir}")
    print(f"  Phase: review_done")
    print()
    print("Next: python3 -m dev_cycle.cli generate-followup")
    print("Then: address findings, implement fixes")
    print("Then: python3 -m dev_cycle.cli check-cycle")
    print("Then: python3 -m dev_cycle.cli finalize-cycle")


# ── generate-followup ────────────────────────────────────────

def cmd_generate_followup(args: argparse.Namespace) -> None:
    cfg = Config.load(Path(args.project_root))
    cycle_dir = _resolve_dir(cfg, args.cycle_dir)
    draft = generate_followup_draft(cycle_dir)

    if not draft:
        print("No review findings to generate followup from.", file=sys.stderr)
        sys.exit(1)

    followup_path = cycle_dir / "codex-followup.md"
    followup_path.write_text(draft)
    counts = count_findings(cycle_dir)
    meta = _read_meta(cycle_dir)

    if getattr(args, "json", False):
        print(json.dumps({
            "cycle_id": meta["cycle_id"],
            "followup_file": str(followup_path),
            "findings": counts,
        }, indent=2))
        return

    print(f"Follow-up draft: {followup_path}")
    print(f"  Findings to address: {counts['high']} high, {counts['medium']} medium, {counts['low']} low")
    print()
    print("Next:")
    print(f"  1. Edit {followup_path} — accept/defer/reject each finding")
    print(f"  2. Implement accepted fixes")
    print(f"  3. python3 -m dev_cycle.cli check-cycle")
    print(f"  4. python3 -m dev_cycle.cli finalize-cycle [--strict]")


# ── run-review-loop ──────────────────────────────────────────

def cmd_run_review_loop(args: argparse.Namespace) -> None:
    cfg = Config.load(Path(args.project_root))
    cycle_dir = _resolve_dir(cfg, args.cycle_dir)
    is_json = getattr(args, "json", False)

    if not is_json:
        print("Step 1/3: Preparing review...", file=sys.stderr)
    prepare_review(cfg, cycle_dir)

    if not is_json:
        print("Step 2/3: Importing review...", file=sys.stderr)
    raw_text = read_input(args.from_file, args.text)
    review_path = import_review(cycle_dir, raw_text)

    if not is_json:
        print("Step 3/3: Finalizing review...", file=sys.stderr)
    warnings = finalize_review(cfg, cycle_dir)

    counts = count_findings(cycle_dir)
    meta = _read_meta(cycle_dir)

    followup_generated = False
    if args.generate_followup:
        draft = generate_followup_draft(cycle_dir)
        if draft:
            (cycle_dir / "codex-followup.md").write_text(draft)
            followup_generated = True

    ns = next_step(cycle_dir)

    if is_json:
        print(json.dumps({
            "cycle_id": meta["cycle_id"],
            "phase": meta.get("phase", "?"),
            "findings": counts,
            "followup_generated": followup_generated,
            "warnings": warnings,
            "next_command": ns["command"],
            "then_command": ns["then"],
            "rereview_hint": ns["rereview_hint"],
            "strict_ready": ns["strict_ready"],
        }, indent=2))
        return

    if warnings:
        print()
        print("Warnings:")
        for w in warnings:
            print(f"  - {w}")

    print()
    print(f"Review loop complete.")
    print(f"  Cycle:    {meta['cycle_id']}")
    print(f"  Phase:    {meta.get('phase', '?')}")
    print(f"  Findings: {counts['high']} high, {counts['medium']} medium, {counts['low']} low")
    if followup_generated:
        print(f"  Followup: draft generated")

    print()
    if counts["total"] == 0:
        print("No findings. You can finalize directly:")
        print(f"  $ python3 -m dev_cycle.cli finalize-cycle")
    elif counts["high"] > 0:
        print(f"HIGH findings — address before finalizing.")
        if not followup_generated:
            print(f"  1. python3 -m dev_cycle.cli generate-followup")
        print(f"  {'1' if followup_generated else '2'}. Edit codex-followup.md — accept/defer/reject")
        print(f"  {'2' if followup_generated else '3'}. Implement fixes")
        print(f"  {'3' if followup_generated else '4'}. python3 -m dev_cycle.cli finalize-cycle --strict")
    else:
        print("No HIGH findings. Address medium/low or finalize:")
        if not followup_generated:
            print(f"  $ python3 -m dev_cycle.cli generate-followup")
        print(f"  $ python3 -m dev_cycle.cli finalize-cycle")


# ── finalize-cycle ───────────────────────────────────────────

def cmd_finalize_cycle(args: argparse.Namespace) -> None:
    cfg = Config.load(Path(args.project_root))
    cycle_dir = _resolve_dir(cfg, args.cycle_dir)
    try:
        warnings = finalize_cycle(cfg, cycle_dir, strict=args.strict)
    except StrictFinalizeError as e:
        print("Strict mode: refusing to finalize.", file=sys.stderr)
        for w in e.warnings:
            print(f"  - {w}", file=sys.stderr)
        sys.exit(1)
    meta = _read_meta(cycle_dir)

    if getattr(args, "json", False):
        print(json.dumps({
            "cycle_id": meta["cycle_id"],
            "phase": meta.get("phase", "?"),
            "status": meta.get("status", "?"),
            "warnings": warnings,
            "finished_at": meta.get("finished_at", ""),
        }, indent=2))
        return

    if warnings:
        print("Warnings:")
        for w in warnings:
            print(f"  - {w}")
        print()
    print(f"Cycle finalized: {cycle_dir}")


# ── check-cycle ──────────────────────────────────────────────

def cmd_check_cycle(args: argparse.Namespace) -> None:
    cfg = Config.load(Path(args.project_root))
    cycle_dir = _resolve_dir(cfg, args.cycle_dir)
    result = check_cycle(cycle_dir)
    meta = _read_meta(cycle_dir)
    counts = count_findings(cycle_dir)

    if args.json:
        print(json.dumps({
            "cycle_id": meta["cycle_id"],
            "phase": result["phase"],
            "ready": result["ready"],
            "placeholder": result["placeholder"],
            "missing": result["missing"],
            "section_warnings": result["section_warnings"],
            "findings": counts,
            "can_finalize": result["can_finalize"],
            "strict_ready": not result["all_issues"],
        }, indent=2))
        if result["all_issues"]:
            sys.exit(1)
        return

    print(f"Cycle:    {meta['cycle_id']}")
    print(f"Phase:    {result['phase']}")
    print(f"Quality:  {len(result['ready'])} ready, {len(result['placeholder'])} placeholder, {len(result['missing'])} missing")
    if counts["total"] > 0:
        print(f"Findings: {counts['high']} high, {counts['medium']} medium, {counts['low']} low")
    print()

    if result["ready"]:
        for r in result["ready"]:
            print(f"  + {r}")
    if result["placeholder"]:
        for p in result["placeholder"]:
            print(f"  ~ {p}")
    if result["missing"]:
        for m in result["missing"]:
            print(f"  ! {m}")
    if result["section_warnings"]:
        for s in result["section_warnings"]:
            print(f"  ! {s}")

    print()
    if not result["all_issues"]:
        print("All checks passed. Ready for strict finalize:")
        print("  $ python3 -m dev_cycle.cli finalize-cycle --strict")
    elif result["can_finalize"]:
        print("Can finalize (with warnings):")
        print("  $ python3 -m dev_cycle.cli finalize-cycle")
        print("Fill remaining files for strict finalize.")
    else:
        print("Not ready to finalize. Fill required files first.")
        ns = next_step(cycle_dir)
        print(f"  Suggested: {ns['action']}")

    if result["all_issues"]:
        sys.exit(1)


# ── next-step ────────────────────────────────────────────────

def cmd_next_step(args: argparse.Namespace) -> None:
    cfg = Config.load(Path(args.project_root))
    cycle_dir = _resolve_dir(cfg, args.cycle_dir)
    ns = next_step(cycle_dir)

    if args.json:
        print(json.dumps(ns, indent=2))
        return

    print(f"Cycle:    {ns['cycle_id']}")
    print(f"Phase:    {ns['phase']}")
    print(f"Quality:  {ns['ready_count']} ready / {ns['placeholder_count']} placeholder / {ns['missing_count']} missing")
    if ns["findings_total"] > 0:
        print(f"Findings: {ns['findings_high']} high / {ns['findings_medium']} medium / {ns['findings_low']} low")
    if ns["phase"] != "started" and ns["phase"] != "completed":
        strict_label = "ready" if ns["strict_ready"] else "not ready" if not ns["can_finalize"] else "warnings"
        print(f"Strict:   {strict_label}")
    if ns["rereview_hint"] not in ("unknown", "not_needed") and ns["phase"] != "completed":
        print(f"Re-review: {ns['rereview_hint']}")
    print()
    print(f"Next: {ns['action']}")
    print(f"  $ {ns['command']}")
    if ns["then"]:
        print(f"Then: $ {ns['then']}")


# ── show-index ───────────────────────────────────────────────

def cmd_show_index(args: argparse.Namespace) -> None:
    cfg = Config.load(Path(args.project_root))

    if args.live:
        entries = _scan_live_cycles(cfg)
    else:
        entries = load_index(cfg)

    if args.version:
        entries = [e for e in entries if e.get("version") == args.version]
    if args.status:
        entries = [e for e in entries if e.get("status") == args.status]
    if args.phase:
        entries = [e for e in entries if e.get("phase") == args.phase]

    if not entries:
        print("No cycles found.")
        return

    if args.format == "markdown":
        if args.detailed:
            print("| Cycle ID | Version | Title | Phase | Started | Finished |")
            print("|----------|---------|-------|-------|---------|----------|")
            for e in entries:
                phase = e.get("phase", e.get("status", "?"))
                started = e.get("started_at", "")[:10]
                finished = e.get("finished_at", "") or ""
                if finished:
                    finished = finished[:10]
                print(f"| `{e['cycle_id']}` | {e['version']} | {e['title']} | {phase} | {started} | {finished} |")
        else:
            print("| Version | Title | Phase |")
            print("|---------|-------|-------|")
            for e in entries:
                phase = e.get("phase", e.get("status", "?"))
                print(f"| {e['version']} | {e['title']} | {phase} |")
    else:
        for e in entries:
            print(json.dumps(e))


def _scan_live_cycles(cfg: Config) -> list[dict]:
    root = cfg.cycle_root_path
    if not root.exists():
        return []
    entries = []
    for d in sorted(root.iterdir()):
        meta_path = d / "meta.json"
        if d.is_dir() and meta_path.exists():
            entries.append(json.loads(meta_path.read_text()))
    return entries


# ── latest-cycle ─────────────────────────────────────────────

def cmd_latest_cycle(args: argparse.Namespace) -> None:
    cfg = Config.load(Path(args.project_root))
    latest = find_latest_cycle(cfg)
    if not latest:
        print("No cycles found.", file=sys.stderr)
        sys.exit(1)
    if args.verbose:
        meta = _read_meta(latest)
        phase = meta.get("phase", meta.get("status", "?"))
        print(f"Path:    {latest}")
        print(f"Cycle:   {meta['cycle_id']}")
        print(f"Version: {meta['version']}")
        print(f"Title:   {meta['title']}")
        print(f"Phase:   {phase}")
        print(f"Started: {meta.get('started_at', 'N/A')}")
    else:
        print(latest)


# ── mark-phase / setup-hooks / append-history ────────────────

def cmd_mark_phase(args: argparse.Namespace) -> None:
    cfg = Config.load(Path(args.project_root))
    cycle_dir = _resolve_dir(cfg, args.cycle_dir)
    meta = _read_meta(cycle_dir)
    _update_phase(meta, args.phase)
    _write_meta(cycle_dir, meta)
    print(f"Phase updated to: {args.phase}")


def cmd_setup_hooks(args: argparse.Namespace) -> None:
    import subprocess
    root = Path(args.project_root).resolve()
    hooks_dir = root / "scripts" / "hooks"
    if not hooks_dir.exists():
        print(f"No scripts/hooks/ directory in {root}", file=sys.stderr)
        sys.exit(1)
    try:
        subprocess.run(
            ["git", "config", "core.hooksPath", "scripts/hooks"],
            cwd=root, check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Failed to configure hooks: {e}", file=sys.stderr)
        sys.exit(1)
    print("Git hooks path set to scripts/hooks/")
    hook = hooks_dir / "post-commit"
    if hook.exists():
        print("  post-commit: auto-tag on vX.Y.Z commit messages")
    sample = hooks_dir / "post-prepare-review.sample"
    if sample.exists():
        installed = hooks_dir / "post-prepare-review"
        if installed.exists():
            print("  post-prepare-review: auto Codex review trigger")
        else:
            print(f"  post-prepare-review: sample available (cp {sample} {installed})")


def cmd_append_history(args: argparse.Namespace) -> None:
    cfg = Config.load(Path(args.project_root))
    cycle_dir = _resolve_dir(cfg, args.cycle_dir)
    meta = _read_meta(cycle_dir)
    from .cycle import _append_version_history
    _append_version_history(cfg, meta, cycle_dir)
    print(f"Appended to {cfg.version_history_path}")


# ── run / resume / status (orchestrator) ─────────────────────

def cmd_run(args: argparse.Namespace) -> None:
    from .orchestrator import run_cycle
    cfg = Config.load(Path(args.project_root))

    if getattr(args, "json", False):
        def output(msg):
            print(msg, file=sys.stderr)
    else:
        def output(msg):
            print(msg)

    result = run_cycle(cfg, args.version, args.title, output_fn=output)

    if getattr(args, "json", False):
        print(json.dumps({
            "cycle_id": result.cycle_id,
            "state": result.state.value,
            "interrupted": result.interrupted,
            "error": result.error,
            "history": result.history,
            "cycle_dir": str(result.cycle_dir),
        }, indent=2))


def cmd_resume(args: argparse.Namespace) -> None:
    from .orchestrator import resume_cycle
    cfg = Config.load(Path(args.project_root))
    cycle_dir = _resolve_dir(cfg, args.cycle_dir)

    if getattr(args, "json", False):
        def output(msg):
            print(msg, file=sys.stderr)
    else:
        def output(msg):
            print(msg)

    result = resume_cycle(cfg, cycle_dir, output_fn=output)

    if getattr(args, "json", False):
        print(json.dumps({
            "cycle_id": result.cycle_id,
            "state": result.state.value,
            "interrupted": result.interrupted,
            "error": result.error,
            "history": result.history,
        }, indent=2))


def cmd_status(args: argparse.Namespace) -> None:
    from .orchestrator import get_status
    cfg = Config.load(Path(args.project_root))
    cycle_dir = _resolve_dir(cfg, args.cycle_dir)
    status = get_status(cfg, cycle_dir)

    if getattr(args, "json", False):
        print(json.dumps(status, indent=2))
        return

    # Git info
    branch = status.get("branch", "")
    sha = status.get("head_sha", "")
    dirty = status.get("dirty", False)
    git_line = branch
    if sha:
        git_line += f" ({sha})"
    if dirty:
        git_line += " [dirty]"

    print(f"Cycle:    {status['cycle_id']}")
    print(f"State:    {status['state']}")
    print(f"Progress: {status['progress_pct']}%")
    if git_line:
        print(f"Branch:   {git_line}")
    q = status["quality"]
    print(f"Quality:  {q['ready']} ready / {q['placeholder']} placeholder / {q['missing']} missing")
    f = status["findings"]
    if f["total"] > 0:
        print(f"Findings: {f['high']} high / {f['medium']} medium / {f['low']} low")
    if q.get("strict_ready"):
        print(f"Strict:   ready")
    print()

    if status["choices"]:
        print("Available actions:")
        for c in status["choices"]:
            print(f"  {c['key']}. {c['label']}")
        print()
        print("Continue: devcycle resume")
    elif status["available_actions"]:
        action = status["available_actions"][0]
        auto_label = " (auto)" if action["auto"] else ""
        print(f"Next: {action['description']}{auto_label}")
        print()
        print("Continue: devcycle resume")


# ── doctor ───────────────────────────────────────────────────

def cmd_doctor(args: argparse.Namespace) -> None:
    from .doctor import run_doctor, format_doctor
    result = run_doctor(Path(args.project_root))
    if getattr(args, "json", False):
        print(json.dumps(result, indent=2))
    else:
        print(format_doctor(result))
    if result["status"] == "error":
        sys.exit(1)


# ── completion ───────────────────────────────────────────────

def cmd_completion(args: argparse.Namespace) -> None:
    from .completion import bash_completion, zsh_completion
    shell = args.shell
    if shell == "bash":
        print(bash_completion())
    elif shell == "zsh":
        print(zsh_completion())
    else:
        print(f"Unsupported shell: {shell}", file=sys.stderr)
        sys.exit(1)


# ── helpers ──────────────────────────────────────────────────

def _add(sub, names, *, help, **kwargs):
    """Register a subcommand with primary name + aliases."""
    if isinstance(names, str):
        names = [names]
    p = sub.add_parser(names[0], aliases=names[1:], help=help, **kwargs)
    return p


def _cycle_dir_arg(p):
    p.add_argument("--cycle-dir", default=None, help="Cycle directory (default: latest)")
    return p


def _json_arg(p):
    p.add_argument("--json", action="store_true", help="Output as JSON")
    return p


# ── main ─────────────────────────────────────────────────────

def main() -> None:
    from . import __version__

    parser = argparse.ArgumentParser(
        prog="devcycle",
        description=(
            "AI Dev Cycle Framework — Claude→Codex→Claude orchestrator.\n\n"
            "Quick start:\n"
            "  devcycle run --version v0.1.0 --title 'my feature'\n"
            "  devcycle resume    # continue an interrupted cycle\n"
            "  devcycle status    # show current state\n\n"
            "The orchestrator runs each phase automatically and prompts\n"
            "for input only at decision points (review input, fix decisions).\n\n"
            "Manual mode (advanced):\n"
            "  start → prepare → review-loop → followup → check → finalize"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--project-root", default=".",
        help="Project root directory (default: current directory)",
    )
    parser.add_argument(
        "--version", action="version", version=f"devcycle {__version__}",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── Orchestrator (primary) ──────────────────────────────

    p = _add(sub, ["run"],
             help="Run a full cycle — auto-executes steps, prompts at decision points")
    p.add_argument("--version", required=True, help="Version label (e.g. v0.1.0)")
    p.add_argument("--title", required=True, help="Short cycle title")
    _json_arg(p)
    p.set_defaults(func=cmd_run)

    p = _add(sub, ["resume"],
             help="Continue an interrupted cycle from where it stopped")
    _cycle_dir_arg(p)
    _json_arg(p)
    p.set_defaults(func=cmd_resume)

    p = _add(sub, ["status"],
             help="Show current cycle state, progress, and available actions")
    _cycle_dir_arg(p)
    _json_arg(p)
    p.set_defaults(func=cmd_status)

    # ── Manual workflow (advanced) ───────────────────────────

    p = _add(sub, ["start", "start-cycle"],
             help="Start a new development cycle")
    p.add_argument("--version", required=True, help="Version label (e.g. v0.1.0)")
    p.add_argument("--title", required=True, help="Short cycle title")
    _json_arg(p)
    p.set_defaults(func=cmd_start_cycle)

    p = _add(sub, ["prepare", "prepare-review"],
             help="Prepare for Codex review — shows prompt and import commands")
    _cycle_dir_arg(p)
    _json_arg(p)
    p.set_defaults(func=cmd_prepare_review)

    p = _add(sub, ["review-loop", "run-review-loop"],
             help="Import Codex review (prepare + import + finalize in one step)",
             description=(
                 "All-in-one: prepare review, import Codex output, finalize review.\n\n"
                 "Input: --from-file, --text, or stdin pipe.\n"
                 "Example: cat codex-output.txt | devcycle review-loop --generate-followup\n"
             ),
             formatter_class=argparse.RawDescriptionHelpFormatter)
    _cycle_dir_arg(p)
    p.add_argument("--from-file", default=None, help="Read review from file")
    p.add_argument("--text", default=None, help="Review text as argument")
    p.add_argument("--generate-followup", action="store_true",
                    help="Also generate codex-followup.md draft")
    _json_arg(p)
    p.set_defaults(func=cmd_run_review_loop)

    p = _add(sub, ["followup", "generate-followup"],
             help="Generate follow-up draft from review findings",
             description=(
                 "Reads codex-review.md, generates codex-followup.md with all findings\n"
                 "pre-populated as Accepted items tagged by severity.\n\n"
                 "Output file: <cycle-dir>/codex-followup.md\n"
                 "Format:\n"
                 "  ## Accepted\n"
                 "  - [HIGH] finding: <!-- action taken -->\n"
                 "  - [MEDIUM] finding: <!-- action taken -->\n"
                 "  ## Deferred\n"
                 "  ## Rejected\n\n"
                 "This is a draft — review each item and fill in actions or move to\n"
                 "Deferred/Rejected sections. Then implement accepted fixes."
             ),
             formatter_class=argparse.RawDescriptionHelpFormatter)
    _cycle_dir_arg(p)
    _json_arg(p)
    p.set_defaults(func=cmd_generate_followup)

    p = _add(sub, ["next", "next-step"],
             help="Show current phase, quality, and the next command to run")
    _cycle_dir_arg(p)
    _json_arg(p)
    p.set_defaults(func=cmd_next_step)

    p = _add(sub, ["check", "check-cycle"],
             help="Check cycle quality — shows ready/placeholder/missing files")
    _cycle_dir_arg(p)
    _json_arg(p)
    p.set_defaults(func=cmd_check_cycle)

    p = _add(sub, ["finalize", "finalize-cycle"],
             help="Complete the cycle — updates index and version history")
    _cycle_dir_arg(p)
    p.add_argument("--strict", action="store_true", help="Fail if any quality issues exist")
    _json_arg(p)
    p.set_defaults(func=cmd_finalize_cycle)

    # ── Review details ──────────────────────────────────────

    p = _add(sub, ["handoff", "review-handoff"],
             help="Show Codex prompt + import command (no phase change)")
    _cycle_dir_arg(p)
    _json_arg(p)
    p.set_defaults(func=cmd_review_handoff)

    p = _add(sub, ["import-review"],
             help="Import Codex review output (--from-file, --text, or stdin)")
    _cycle_dir_arg(p)
    p.add_argument("--from-file", default=None, help="Read review from file")
    p.add_argument("--text", default=None, help="Review text as argument")
    _json_arg(p)
    p.set_defaults(func=cmd_import_review)

    p = _add(sub, ["finalize-review"],
             help="Mark review as done, prepare follow-up template")
    _cycle_dir_arg(p)
    p.set_defaults(func=cmd_finalize_review)

    # ── Utilities ───────────────────────────────────────────

    p = _add(sub, ["index", "show-index"],
             help="List cycles (--live, --phase, --format markdown)")
    p.add_argument("--version", default=None, help="Filter by version")
    p.add_argument("--status", default=None, help="Filter by status")
    p.add_argument("--phase", default=None, help="Filter by phase")
    p.add_argument("--live", action="store_true", help="Scan cycle dirs instead of index.jsonl")
    p.add_argument("--detailed", action="store_true", help="Show full details in markdown mode")
    p.add_argument("--format", default="jsonl", choices=["jsonl", "markdown"], help="Output format")
    p.set_defaults(func=cmd_show_index)

    p = _add(sub, ["latest", "latest-cycle"],
             help="Print path of most recent cycle (-v for details)")
    p.add_argument("--verbose", "-v", action="store_true", help="Show details")
    p.set_defaults(func=cmd_latest_cycle)

    p = _add(sub, ["mark-phase"],
             help="Manually set cycle phase")
    _cycle_dir_arg(p)
    p.add_argument("--phase", required=True, choices=PHASES, help="Phase to set")
    p.set_defaults(func=cmd_mark_phase)

    p = _add(sub, ["setup-hooks"],
             help="Configure git to use project hooks (auto-tag)")
    p.set_defaults(func=cmd_setup_hooks)

    p = _add(sub, ["append-history"],
             help="Append cycle entry to version history")
    _cycle_dir_arg(p)
    p.set_defaults(func=cmd_append_history)

    # ── Diagnostics ─────────────────────────────────────────

    p = _add(sub, ["doctor"],
             help="Check environment setup — config, hooks, write access")
    _json_arg(p)
    p.set_defaults(func=cmd_doctor)

    p = _add(sub, ["completion"],
             help="Generate shell completion script (bash or zsh)")
    p.add_argument("shell", choices=["bash", "zsh"], help="Target shell")
    p.set_defaults(func=cmd_completion)

    args = parser.parse_args()
    try:
        args.func(args)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("Run 'devcycle doctor' to check your setup.", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print(file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
