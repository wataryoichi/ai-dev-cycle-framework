"""Integration test — run a full cycle from start to finalize."""

from __future__ import annotations

import json
from pathlib import Path

from dev_cycle.config import Config
from dev_cycle.cycle import (
    _read_meta,
    check_cycle,
    finalize_cycle,
    next_step,
    start_cycle,
)
from dev_cycle.review_importer import (
    count_findings,
    generate_followup_draft,
    import_review,
)
from dev_cycle.review_orchestrator import finalize_review, prepare_review


def test_full_cycle(cfg: Config) -> None:
    """End-to-end: start → implement → review → followup → finalize."""

    # 1. Start cycle
    cycle_dir = start_cycle(cfg, "v1.0.0", "integration test")
    meta = _read_meta(cycle_dir)
    assert meta["phase"] == "started"

    # 2. Simulate implementation (fill required files)
    (cycle_dir / "request.md").write_text("# Request\n\n## Goal\nTest.\n")
    (cycle_dir / "claude-implementation-summary.md").write_text(
        "# Summary\n\n## What Was Done\nImplemented feature.\n"
        "## Key Decisions\nNone.\n## Changed Files\n- foo.py\n"
        "## Testing\nUnit tests.\n"
    )

    # 3. Prepare review
    info = prepare_review(cfg, cycle_dir)
    meta = _read_meta(cycle_dir)
    assert meta["phase"] == "review_pending"
    assert info["title"] == "integration test"

    # 4. Import review
    review_text = (
        "Good implementation.\n"
        "- Critical: missing error handling in foo.py\n"
        "- Should add input validation\n"
        "- Minor: typo in docstring\n"
    )
    review_path = import_review(cycle_dir, review_text)
    meta = _read_meta(cycle_dir)
    assert meta["phase"] == "review_imported"

    counts = count_findings(cycle_dir)
    assert counts["high"] >= 1
    assert counts["total"] >= 3

    # 5. Finalize review
    warnings = finalize_review(cfg, cycle_dir)
    meta = _read_meta(cycle_dir)
    assert meta["phase"] == "review_done"

    # 6. Generate followup
    draft = generate_followup_draft(cycle_dir)
    assert "[HIGH]" in draft
    (cycle_dir / "codex-followup.md").write_text(
        "# Followup\n\n## Accepted\n"
        "- [HIGH] Error handling: added try/except in foo.py\n"
        "- [MEDIUM] Input validation: added checks\n\n"
        "## Deferred\n- [LOW] Typo: next cycle\n\n"
        "## Rejected\n\n## Additional Notes\n"
    )

    # 7. Check next-step
    ns = next_step(cycle_dir)
    assert ns["rereview_hint"] == "recommended"  # HIGH was accepted
    assert ns["findings_total"] >= 3

    # 8. Write final summary
    (cycle_dir / "final-summary.md").write_text(
        "# Final Summary\n\n## Overview\nCompleted integration test.\n\n"
        "## Changes\n- foo.py: added error handling\n\n"
        "## Verification\nAll tests pass.\n\n"
        "## Remaining Issues\n- Typo fix deferred.\n"
    )

    # 9. Check cycle quality
    result = check_cycle(cycle_dir)
    assert not result["all_issues"]
    assert result["can_finalize"]

    # 10. Finalize
    warnings = finalize_cycle(cfg, cycle_dir, strict=True)
    assert warnings == []
    meta = _read_meta(cycle_dir)
    assert meta["phase"] == "completed"
    assert meta["status"] == "completed"
    assert meta["finished_at"] is not None

    # 11. Verify index and history
    index_path = cfg.cycle_root_path / "index.jsonl"
    assert index_path.exists()
    entries = [json.loads(l) for l in index_path.read_text().splitlines() if l.strip()]
    assert any(e["cycle_id"] == meta["cycle_id"] for e in entries)

    history = cfg.version_history_path.read_text()
    assert "v1.0.0" in history
    assert "integration test" in history
