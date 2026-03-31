"""Tests for shell completion generation."""

from __future__ import annotations

from dev_cycle.completion import bash_completion, zsh_completion, SUBCOMMANDS


class TestBashCompletion:
    def test_generates_output(self) -> None:
        output = bash_completion()
        assert len(output) > 100

    def test_contains_function(self) -> None:
        output = bash_completion()
        assert "_devcycle()" in output
        assert "complete -F _devcycle devcycle" in output

    def test_contains_subcommands(self) -> None:
        output = bash_completion()
        for cmd in ["start", "next", "finalize", "doctor", "followup", "check"]:
            assert cmd in output


class TestZshCompletion:
    def test_generates_output(self) -> None:
        output = zsh_completion()
        assert len(output) > 100

    def test_contains_compdef(self) -> None:
        output = zsh_completion()
        assert "#compdef devcycle" in output

    def test_contains_subcommands(self) -> None:
        output = zsh_completion()
        for cmd in ["start", "next", "finalize", "doctor", "followup"]:
            assert cmd in output


class TestSubcommandList:
    def test_doctor_in_list(self) -> None:
        assert "doctor" in SUBCOMMANDS

    def test_completion_in_list(self) -> None:
        assert "completion" in SUBCOMMANDS
