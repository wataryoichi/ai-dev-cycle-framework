"""Internationalization — locale-aware labels for Markdown output.

JSON keys and internal identifiers stay English.
Only human-facing Markdown headings and template text are localized.
"""

from __future__ import annotations

LOCALES: dict[str, dict[str, str]] = {
    "en": {
        "request_title": "Request",
        "goal": "Goal",
        "context": "Context",
        "scope": "Scope",
        "notes": "Notes",
        "spec": "Spec",
        "constraints": "Constraints",
        "expected_outputs": "Expected Outputs",
        "impl_title": "Claude Implementation Summary",
        "what_was_done": "What Was Done",
        "key_decisions": "Key Decisions",
        "changed_files": "Changed Files",
        "testing": "Testing",
        "known_limitations": "Known Limitations",
        "review_title": "Codex Review",
        "reviewer": "Reviewer",
        "summary": "Summary",
        "findings": "Findings",
        "high": "High",
        "medium": "Medium",
        "low": "Low",
        "raw_notes": "Raw Notes",
        "followup_title": "Codex Follow-up",
        "accepted": "Accepted",
        "deferred": "Deferred",
        "rejected": "Rejected",
        "additional_notes": "Additional Notes",
        "final_title": "Final Summary",
        "overview": "Overview",
        "changes": "Changes",
        "verification": "Verification",
        "remaining_issues": "Remaining Issues",
        "rollback_title": "Rollback",
        "from": "From",
        "to": "To",
        "tag": "Tag",
        "reason": "Reason",
        "time": "Time",
        "previous_cycle": "Previous Cycle",
        "carried_forward": "Carried Forward Context",
        "outstanding_findings": "Outstanding Findings",
        "placeholder_goal": "<!-- Describe the goal -->",
        "placeholder_context": "<!-- Why is this needed? -->",
        "placeholder_scope": "<!-- In scope / out of scope -->",
        "placeholder_notes": "<!-- Constraints, dependencies -->",
    },
    "ja": {
        "request_title": "リクエスト",
        "goal": "目的",
        "context": "背景",
        "scope": "スコープ",
        "notes": "補足",
        "spec": "仕様",
        "constraints": "制約",
        "expected_outputs": "期待する出力",
        "impl_title": "Claude 実装サマリー",
        "what_was_done": "実装内容",
        "key_decisions": "主要な判断",
        "changed_files": "変更ファイル",
        "testing": "テスト",
        "known_limitations": "既知の制限",
        "review_title": "Codex レビュー",
        "reviewer": "レビュアー",
        "summary": "概要",
        "findings": "指摘事項",
        "high": "高",
        "medium": "中",
        "low": "低",
        "raw_notes": "生ノート",
        "followup_title": "Codex フォローアップ",
        "accepted": "採用",
        "deferred": "延期",
        "rejected": "却下",
        "additional_notes": "追加メモ",
        "final_title": "最終サマリー",
        "overview": "概要",
        "changes": "変更点",
        "verification": "検証",
        "remaining_issues": "残課題",
        "rollback_title": "ロールバック",
        "from": "元",
        "to": "先",
        "tag": "タグ",
        "reason": "理由",
        "time": "実行時刻",
        "previous_cycle": "前サイクル",
        "carried_forward": "引き継ぎコンテキスト",
        "outstanding_findings": "未解決の指摘",
        "placeholder_goal": "<!-- 目的を記述 -->",
        "placeholder_context": "<!-- なぜ必要か -->",
        "placeholder_scope": "<!-- スコープ内/外 -->",
        "placeholder_notes": "<!-- 制約、依存関係 -->",
    },
}

DEFAULT_LANG = "en"


def get_labels(lang: str | None = None) -> dict[str, str]:
    """Get locale labels. Falls back to English."""
    return LOCALES.get(lang or DEFAULT_LANG, LOCALES["en"])


def resolve_lang(cli_lang: str | None = None, config_lang: str | None = None) -> str:
    """Resolve language from CLI arg, config, or default."""
    if cli_lang:
        return cli_lang
    if config_lang:
        return config_lang
    return DEFAULT_LANG


# Locale-aware section aliases for state/quality detection.
# Maps semantic key → list of heading variants across all supported locales.
SECTION_ALIASES: dict[str, list[str]] = {
    "goal": ["## Goal", "## 目的"],
    "overview": ["## Overview", "## 概要"],
    "changes": ["## Changes", "## 変更点"],
    "what_was_done": ["## What Was Done", "## 実装内容"],
    "context": ["## Context", "## 背景"],
    "scope": ["## Scope", "## スコープ"],
}

# Placeholder patterns that indicate unfilled template content
PLACEHOLDER_PATTERNS: list[str] = [
    "<!-- Describe", "<!-- 目的を記述",
    "<!-- Why is this needed", "<!-- なぜ必要か",
]


def has_section(content: str, section_key: str) -> bool:
    """Check if content has a section matching any locale variant."""
    for alias in SECTION_ALIASES.get(section_key, []):
        if alias in content:
            return True
    return False


def has_placeholder(content: str) -> bool:
    """Check if content has any locale placeholder pattern."""
    for p in PLACEHOLDER_PATTERNS:
        if p in content:
            return True
    return False
