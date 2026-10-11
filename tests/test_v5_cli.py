"""CLI smoke tests exercise the real entry point with a reproducible seed."""
import sys

from kimarite import play_human


def test_cli_can_open_bout_and_quit(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["kimarite.play_human", "--seed", "20261009"])
    monkeypatch.setattr("builtins.input", lambda _: "quit")
    play_human.main()
    output = capsys.readouterr().out
    assert "KIMARITE" in output
    assert "Bout seed: 20261009" in output
    assert "Playable:" in output
    assert "Session ended without recording a victory." in output


def test_cli_can_pass_turn_and_reach_next_prompt(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["kimarite.play_human", "--seed", "20261009"])
    replies = iter(["pass", "quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(replies))
    play_human.main()
    output = capsys.readouterr().out
    assert "KIMARITE" in output
    assert "Your plays remaining" in output
    assert (
        "Session ended without recording a victory." in output
        or "Opponent won by" in output
        or "You won by" in output
    )

