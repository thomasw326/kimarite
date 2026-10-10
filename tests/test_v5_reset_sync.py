"""Current Reset to Neutral card removes both Temporary zones."""
from kimarite.catalog import card_by_name
from kimarite.effects import EffectContext, resolve_exchange_effect
from kimarite.models import BoutState, FighterState, GripState, Side, Wrestler
from kimarite.temporary import add_temporary


def test_reset_to_neutral_clears_both_temporaries_and_own_grip():
    starter = card_by_name("Oshidashi")
    a = Wrestler("A", 2, 2, 2, starter, starter, starter)
    b = Wrestler("B", 2, 2, 2, starter, starter, starter)
    state = BoutState(FighterState(a), FighterState(b), momentum=-1)
    state.fighter_a.left_grip = GripState.GRIP
    add_temporary(state, Side.A, card_by_name("Hold Position"), phase="exchange")
    add_temporary(state, Side.B, card_by_name("Immovable"), phase="exchange")
    resolve_exchange_effect(state, Side.A, card_by_name("Reset to Neutral"), EffectContext())
    assert not state.fighter_a.temporary_zone
    assert not state.fighter_b.temporary_zone
    assert state.fighter_a.total_grip == 0
    assert state.momentum == 0
    assert state.position == 1
