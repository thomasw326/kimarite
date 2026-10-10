"""Human defender owns Kimarite search prompted by Get Underneath."""
import pytest
from kimarite.catalog import card_by_name
from kimarite.effects import give_opponent_kimarite
from kimarite.human_bout import HumanBout
from kimarite.models import BoutState, FighterState, Side, Wrestler
from kimarite.tachiai import compare_tachiai


def test_opponent_owned_search_defers_until_human_selects():
    starter = card_by_name("Oshidashi")
    a = Wrestler("A", 2, 2, 2, starter, starter, starter)
    b = Wrestler("B", 2, 2, 2, starter, starter, starter)
    state = BoutState(FighterState(a), FighterState(b))
    state.human_choice_side = Side.B
    state.fighter_b.draw_pile = [card_by_name("Yorikiri"), card_by_name("Oshi"),
                                  card_by_name("Oshidashi")]
    give_opponent_kimarite(state, Side.A, "Get Underneath")
    assert len(state.pending_kimarite_searches) == 1
    assert not state.fighter_b.kimarite_zone
    bout = HumanBout(state, compare_tachiai(a, b), Side.B, lambda *args: None)
    bout.advance()
    assert bout.awaiting_human
    assert len(bout.pending_kimarite_search) == 2
    with pytest.raises(Exception):
        bout.choose_kimarite_search(1)
    assert len(state.pending_kimarite_searches) == 1
    bout.choose_kimarite_search(2)
    assert state.fighter_b.kimarite_zone[0].name == "Oshidashi"
    assert not state.pending_kimarite_searches
