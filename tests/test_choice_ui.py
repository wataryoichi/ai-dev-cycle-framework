"""Tests for choice UI — monkeypatch stdin."""

from __future__ import annotations

import pytest

from dev_cycle.choice_ui import prompt_choice, prompt_confirm
from dev_cycle.state_machine import Choice


@pytest.fixture
def sample_choices() -> list[Choice]:
    return [
        Choice(1, "Do thing A", "action_a"),
        Choice(2, "Do thing B", "action_b"),
        Choice(3, "Exit", "exit"),
    ]


class TestPromptChoice:
    def test_enter_selects_default(self, monkeypatch, sample_choices) -> None:
        monkeypatch.setattr("builtins.input", lambda _: "")
        result = prompt_choice(sample_choices)
        assert result.key == 1  # first choice is default

    def test_explicit_number(self, monkeypatch, sample_choices) -> None:
        monkeypatch.setattr("builtins.input", lambda _: "2")
        result = prompt_choice(sample_choices)
        assert result.key == 2
        assert result.action == "action_b"

    def test_explicit_exit(self, monkeypatch, sample_choices) -> None:
        monkeypatch.setattr("builtins.input", lambda _: "3")
        result = prompt_choice(sample_choices)
        assert result.action == "exit"

    def test_invalid_then_valid(self, monkeypatch, sample_choices) -> None:
        inputs = iter(["99", "abc", "2"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        result = prompt_choice(sample_choices)
        assert result.key == 2

    def test_eof_returns_exit_choice(self, monkeypatch, sample_choices) -> None:
        monkeypatch.setattr("builtins.input", lambda _: (_ for _ in ()).throw(EOFError))
        result = prompt_choice(sample_choices)
        assert result.action == "exit"

    def test_keyboard_interrupt_returns_exit(self, monkeypatch, sample_choices) -> None:
        monkeypatch.setattr("builtins.input", lambda _: (_ for _ in ()).throw(KeyboardInterrupt))
        result = prompt_choice(sample_choices)
        assert result.action == "exit"


class TestPromptConfirm:
    def test_yes(self, monkeypatch) -> None:
        monkeypatch.setattr("builtins.input", lambda _: "y")
        assert prompt_confirm("Continue?") is True

    def test_no(self, monkeypatch) -> None:
        monkeypatch.setattr("builtins.input", lambda _: "n")
        assert prompt_confirm("Continue?") is False

    def test_empty_is_no(self, monkeypatch) -> None:
        monkeypatch.setattr("builtins.input", lambda _: "")
        assert prompt_confirm("Continue?") is False

    def test_eof_is_no(self, monkeypatch) -> None:
        monkeypatch.setattr("builtins.input", lambda _: (_ for _ in ()).throw(EOFError))
        assert prompt_confirm("Continue?") is False
