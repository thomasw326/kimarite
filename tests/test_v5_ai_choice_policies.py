"""AI choices use the currently printed Pull and Read the Move mode keys."""
from kimarite.ai import _contexts_for_card
from kimarite.catalog import card_by_name
from kimarite.models import BoutState, FighterState, Side, Wrestler
from kimarite.tachiai import compare_tachiai
from kimarite.temporary import add_temporary


def setup():
    starter = card_by_name("Oshidashi")
    a = Wrestler("A", 2, 2, 2, starter, starter, starter)
    b = Wrestler("B", 2, 2, 2, starter, starter, starter)
    state = BoutState(FighterState(a), FighterState(b))
    state.fighter_a.hand = [card_by_name("Oshi")]
    state.fighter_a.draw_pile = [card_by_name("Tsuki")]
    return state, compare_tachiai(a, b)


def test_pull_ai_explores_both_printed_modes():
    state, comparison = setup()
    state.fighter_a.discard_pile = [card_by_name("Harite")]
    contexts = _contexts_for_card(state, Side.A, card_by_name("Pull"), comparison)
    assert {c.choice("mode") for c in contexts} == {"filter", "reversal"}


def test_read_the_move_ai_explores_removal_and_draw():
    state, comparison = setup()
    add_temporary(state, Side.B, card_by_name("Pull"), phase="exchange")
    contexts = _contexts_for_card(state, Side.A, card_by_name("Read the Move"), comparison)
    assert {c.choice("mode") for c in contexts} == {"remove", "draw"}
