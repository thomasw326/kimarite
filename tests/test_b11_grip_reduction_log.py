"""Grip reductions are visible in event history without changing game state rules."""
from kimarite.models import BoutState, Card, FighterState, GripState, Side, Wrestler
from kimarite.rules import reduce_grip


def test_left_grip_reduction_logs_level_transition():
    blank = Card(99011, "Blank")
    a = FighterState(Wrestler("Arm Controller", 0, 0, 0, blank, blank, blank))
    b = FighterState(Wrestler("The Technician", 0, 0, 0, blank, blank, blank))
    b.left_grip = GripState.GRIP
    state = BoutState(a, b)
    reduce_grip(state, Side.B)
    assert b.left_grip == GripState.NONE
    assert state.event_log[-1] == "The Technician's Left Grip decreases (GRIP → NONE)."


def test_deep_grip_reduction_shows_each_step():
    blank = Card(99012, "Blank")
    a = FighterState(Wrestler("A", 0, 0, 0, blank, blank, blank))
    b = FighterState(Wrestler("B", 0, 0, 0, blank, blank, blank))
    b.right_grip = GripState.DEEP
    state = BoutState(a, b)
    reduce_grip(state, Side.B, amount=2, hand="right")
    assert b.right_grip == GripState.NONE
    assert state.event_log[-2:] == [
        "B's Right Grip decreases (DEEP → GRIP).",
        "B's Right Grip decreases (GRIP → NONE).",
    ]
