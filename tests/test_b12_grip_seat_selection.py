import pytest
from kimarite.catalog import card_by_name
from kimarite.effects import EffectContext, resolve_exchange_effect
from kimarite.models import BoutState, FighterState, GripState, Side, Wrestler
from kimarite.rules import automatic_grip_hand, gain_flexible_grip, reduce_grip
from kimarite.ai import _best_grip_to_reduce

@pytest.mark.parametrize("side,hand", [(Side.A,"left"),(Side.B,"right")])
def test_seat_ties(side, hand):
    c = card_by_name("Oshi")
    w = Wrestler("W",3,2,1,c,c,c)
    s = BoutState(FighterState(w), FighterState(w))
    own, foe = s.fighter(side), s.opponent(side)
    gain_flexible_grip(s, side)
    assert getattr(own, hand+"_grip") == GripState.GRIP
    assert automatic_grip_hand(s, side) != hand
    own.left_grip = own.right_grip = GripState.NONE
    resolve_exchange_effect(s, side, card_by_name("Attempt Two-Handed Grip"), EffectContext())
    assert getattr(own, hand+"_grip") == GripState.GRIP
    foe.left_grip = foe.right_grip = GripState.DEEP
    assert _best_grip_to_reduce(s, side) == hand
    reduce_grip(s, s.opponent_side(side))
    assert getattr(foe, hand+"_grip") == GripState.GRIP
    assert automatic_grip_hand(s, side, reduce=True) != hand
