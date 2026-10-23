"""Style AI is opt-in; victory beats preferences and missing plays pass."""
from kimarite.catalog import card_by_name
from kimarite.models import BoutState, FighterState, Side, Wrestler
from kimarite.style_ai_v5 import choose_style_play
from kimarite.styles_v5 import STYLES
from kimarite.tachiai import compare_tachiai


def make_state(hand=()):
    starter = card_by_name("Oshidashi")
    w1 = Wrestler("A", 2, 2, 2, starter, starter, starter, ranking=1)
    w2 = Wrestler("B", 2, 2, 2, starter, starter, starter, ranking=2)
    state = BoutState(
        FighterState(w1, hand=[card_by_name(x) for x in hand],
                     draw_pile=[card_by_name("Oshi")]),
        FighterState(w2, draw_pile=[card_by_name("Shove")]),
        active_side=Side.A,
    )
    return state, compare_tachiai(w1, w2)


def test_all_fifteen_styles_accept_empty_hand_without_mutating_state():
    state, comp = make_state()
    for style in STYLES:
        assert choose_style_play(state, Side.A, comp, style) is None
    assert state.card_plays == []


def test_style_ai_selects_and_preserves_input_state():
    state, comp = make_state(("Oshi", "Shove"))
    state.momentum = 1
    choice = choose_style_play(state, Side.A, comp, "Heavy Hitter")
    assert choice is not None
    assert choice.card.name in {"Oshi", "Shove"}
    assert not state.card_plays
    assert [c.name for c in state.fighter_a.hand] == ["Oshi", "Shove"]
