"""CLI smoke tests run through the actual entry point without a terminal."""
import sys

from kimarite import play_human


def test_cli_can_open_bout_and_quit_during_card_access(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["kimarite.play_human"])
    monkeypatch.setattr("builtins.input", lambda _: "quit")
    play_human.main()
    output = capsys.readouterr().out
    assert "KIMARITE" in output
    assert "Looked at" in output


def test_cli_can_keep_cards_and_reach_play_prompt(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["kimarite.play_human"])
    replies = iter(["0 1", "quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(replies))
    play_human.main()
    output = capsys.readouterr().out
    assert "Looked at" in output
    assert "Your plays remaining" in output
    assert "Session ended without recording a victory." in output
