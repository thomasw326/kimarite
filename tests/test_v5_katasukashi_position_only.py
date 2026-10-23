"""V5.1 Katasukashi requires opponent no Grip, positive Momentum and +5 hand advantage."""
from kimarite.catalog import card_by_name
from kimarite.kimarite import kimarite_is_satisfied
from kimarite.models import BoutState, FighterState, Wrestler, Card, Side, GripState


def test_katasukashi_requires_hand_advantage_and_opponent_no_grip():
    k = card_by_name("Katasukashi")
    blank = Card(90100, "Test Blank")
    a = Wrestler("A", 2, 2, 2, k, blank, blank)
    b = Wrestler("B", 2, 2, 2, k, blank, blank)
    state = BoutState(FighterState(a, kimarite_zone=[k], hand=[blank] * 5), FighterState(b))
    state.momentum = 0
    assert not kimarite_is_satisfied(state, Side.A, k)
    state.momentum = 1
    assert kimarite_is_satisfied(state, Side.A, k)
    state.fighter_b.left_grip = GripState.GRIP
    assert not kimarite_is_satisfied(state, Side.A, k)
    state.fighter_b.left_grip = GripState.NONE
    state.fighter_a.hand.pop()
    assert not kimarite_is_satisfied(state, Side.A, k)
