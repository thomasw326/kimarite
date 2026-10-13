"""Read the Move keeps its effect but exhausts after playing."""
from types import SimpleNamespace

from kimarite.models import Side
from kimarite import playing


def test_read_the_move_exhausts_after_effect(monkeypatch):
    card = SimpleNamespace(name="Read the Move", card_id=37, is_kimarite=False)
    fighter = SimpleNamespace(
        wrestler=SimpleNamespace(name="Test"), hand=[card],
        plays_remaining=2, cards_played_this_turn=0,
        played_this_turn=[], discard_pile=[], draw_pile=[],
    )
    messages = []
    state = SimpleNamespace(
        winner=None, card_plays=[], card_play_ids=[],
        fighter=lambda side: fighter, log=messages.append,
    )
    invoked = []
    monkeypatch.setattr(playing, "can_play_card", lambda *args: True)
    monkeypatch.setattr(
        playing, "resolve_exchange_effect",
        lambda state, side, card, context: invoked.append(card.name),
    )
    playing.play_card(state, Side.A, card)
    assert invoked == ["Read the Move"]
    assert card not in fighter.hand
    assert card not in fighter.discard_pile
    assert card not in fighter.draw_pile
    assert any("exhausted" in message for message in messages)
