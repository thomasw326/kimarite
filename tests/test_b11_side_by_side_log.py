"""A Spin Away Side-by-Side lock must not be logged as Sidestep."""
from kimarite.models import BoutState, Card, FighterState, Side, Wrestler
from kimarite.rules import gain_push


def test_side_by_side_push_suppression_names_the_shared_state():
    placeholder = Card(99001, "Blank")
    a = Wrestler("A", 0, 0, 0, placeholder, placeholder, placeholder)
    b = Wrestler("B", 0, 0, 0, placeholder, placeholder, placeholder)
    state = BoutState(FighterState(a), FighterState(b))
    state.side_by_side_owner = Side.B
    state.side_by_side_distance = 2
    gain_push(state, Side.A, 2)
    assert state.position == 0
    assert state.event_log[-1] == "Side-by-Side reduces all Push to 0."
    assert "Sidestep" not in state.event_log[-1]
