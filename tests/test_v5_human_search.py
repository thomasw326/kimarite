"""Search automatically takes the first category match in Draw Pile order."""
from kimarite.catalog import card_by_name
from kimarite.effects import give_opponent_kimarite
from kimarite.models import BoutState, FighterState, Side, Wrestler


def test_opponent_search_takes_topmost_kimarite_without_human_prompt():
    starter = card_by_name("Oshidashi")
    a = Wrestler("A", 2, 2, 2, starter, starter, starter)
    b = Wrestler("B", 2, 2, 2, starter, starter, starter)
    state = BoutState(FighterState(a), FighterState(b))
    state.fighter_b.draw_pile = [
        card_by_name("Oshi"), card_by_name("Yorikiri"),
        card_by_name("Oshidashi")
    ]
    give_opponent_kimarite(state, Side.A, "Get Underneath")
    assert [c.name for c in state.fighter_b.kimarite_zone] == ["Yorikiri"]
    assert [c.name for c in state.fighter_b.draw_pile] == ["Oshi", "Oshidashi"]
