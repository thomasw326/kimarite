"""Human Uwate choice is transactional, not silently AI-selected."""
from copy import deepcopy
import pytest

from kimarite.actions import submit_card_action
from kimarite.catalog import card_by_name
from kimarite.effects import ChoiceRequired
from kimarite.models import BoutState, FighterState, GripState, Side, Wrestler


def test_human_uwate_requires_look_selection_and_rolls_back():
    starter = card_by_name("Oshidashi")
    wrestler = Wrestler("A", 2, 2, 2, starter, starter, starter)
    state = BoutState(
        FighterState(wrestler, hand=[card_by_name("Uwate")],
                     draw_pile=[card_by_name("Shove"), card_by_name("Tsuri")],
                     left_grip=GripState.GRIP),
        FighterState(wrestler, power=3), active_side=Side.A,
    )
    before = deepcopy(state)
    with pytest.raises(ChoiceRequired) as err:
        submit_card_action(state, Side.A, 0)
    assert err.value.choice_name == "uwate_card_index"
    assert err.value.options == [0, 1]
    assert state == before
    submit_card_action(state, Side.A, 0, choices={"uwate_card_index": 0})
    assert state.card_plays == [(Side.A, "Uwate"), (Side.A, "Shove")]
    assert state.fighter_a.plays_remaining == 1
