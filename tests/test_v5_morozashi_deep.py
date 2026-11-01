"""Morozashi works from one gripping hand, including a Deep Grip."""
import pytest
from kimarite.catalog import card_by_name
from kimarite.legality import can_play_card
from kimarite.models import BoutState, FighterState, GripState, Side, Wrestler
from kimarite.playing import play_card


@pytest.mark.parametrize("hand,depth", [
    ("left", GripState.GRIP),
    ("left", GripState.DEEP),
    ("right", GripState.GRIP),
    ("right", GripState.DEEP),
])
def test_morozashi_adds_other_hand_without_downgrading(hand, depth):
    base = card_by_name("Oshi")
    w = Wrestler("W", 2, 2, 2, base, base, base)
    state = BoutState(FighterState(w), FighterState(w))
    card = card_by_name("Morozashi")
    fighter = state.fighter_a
    fighter.hand.append(card)
    fighter.plays_remaining = 2
    if hand == "left":
        fighter.left_grip = depth
    else:
        fighter.right_grip = depth
    assert can_play_card(state, Side.A, card)
    play_card(state, Side.A, card)
    assert fighter.left_grip == (depth if hand == "left" else GripState.GRIP)
    assert fighter.right_grip == (depth if hand == "right" else GripState.GRIP)
    assert any(x.card.name == "Morozashi" for x in fighter.temporary_zone)


@pytest.mark.parametrize("left,right", [
    (GripState.NONE, GripState.NONE),
    (GripState.GRIP, GripState.GRIP),
    (GripState.DEEP, GripState.GRIP),
])
def test_morozashi_requires_at_least_one_gripping_hand(left, right):
    base = card_by_name("Oshi")
    w = Wrestler("W", 2, 2, 2, base, base, base)
    state = BoutState(FighterState(w), FighterState(w))
    card = card_by_name("Morozashi")
    state.fighter_a.hand.append(card)
    state.fighter_a.plays_remaining = 2
    state.fighter_a.left_grip = left
    state.fighter_a.right_grip = right
    # B11: already having both Grips is legal; only zero Grip is invalid.
    assert can_play_card(state, Side.A, card) is (left != GripState.NONE or right != GripState.NONE)
