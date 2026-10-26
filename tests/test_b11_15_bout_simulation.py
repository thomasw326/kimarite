"""Automated 15-bout B11 tournament smoke using live human-vs-AI engine.

The human is driven by the existing style AI only for testing. This covers
real turn starts, card access, card plays, AI turns and terminal handling;
it does not replace a human 15-bout UI playtest.
"""
from kimarite.b10_human_session import management_deal, roster, STYLE_PROXIES
from kimarite.b11_pending_session import PendingB11Session
from kimarite.b11_live_opening import start_b11_human_bout
from kimarite.style_ai_v5 import play_style_turn
from kimarite.models import Side


def simulate(seed, human, opponent, allocation, commitments):
    pending = PendingB11Session.start(human, opponent, allocation, seed=seed)
    pending.confirm(commitments)
    game = start_b11_human_bout(pending, max_turns=60)
    for step in range(150):
        if game.finished:
            break
        if game.pending_selection is not None:
            game.choose_cards(list(range(game.pending_selection.keep)))
        if game.finished:
            break
        if game.awaiting_human:
            play_style_turn(
                game.state, Side.A, game.comparison,
                STYLE_PROXIES.get(human, human), max_cards=20,
            )
            if not game.finished:
                game.end_turn()
        else:
            game.advance()
    assert game.finished, (seed, game.state.turn_number, game.stopped_reason)
    assert game.state.turn_number <= 60
    assert game.state.winner is not None, (seed, game.stopped_reason)
    assert any(e.startswith("TURN ") for e in game.state.event_log)
    return (
        game.state.winner.value, game.state.win_method,
        game.state.turn_number, tuple(game.state.event_log)
    )


def test_fifteen_complete_b11_bouts_and_seeded_replay():
    wrestlers = roster()
    human = "Arm Controller"
    opponents = [name for name in wrestlers if name != human][:15]
    assert len(opponents) == 15 and len(set(opponents)) == 15
    for round_number in range(5):
        deal = management_deal(human, seed=178000 + round_number)
        for group in range(3):
            bout_index = round_number * 3 + group
            cards = [deal["cards"][group * 3 + k]["name"] for k in range(3)]
            seed = 178500 + bout_index
            result = simulate(seed, human, opponents[bout_index], cards, list(range(bout_index % 4)))
            if bout_index == 0:
                assert result == simulate(seed, human, opponents[bout_index], cards, [])
