"""V5 transactional action boundary and hidden-information observations."""
from copy import deepcopy

import pytest

from kimarite.actions import legal_actions, observe, submit_card_action
from kimarite.catalog import card_by_name
from kimarite.effects import ChoiceRequired, IllegalPlay
from kimarite.models import BoutState, FighterState, Side, Wrestler


def state_with_hand(*names):
    starter = card_by_name("Oshidashi")
    template = Wrestler("A", 2, 2, 2, starter, starter, starter)
    other = Wrestler("B", 2, 2, 2, starter, starter, starter)
    state = BoutState(
        FighterState(template, hand=[card_by_name(n) for n in names],
                     draw_pile=[card_by_name("Oshi")]),
        FighterState(other, hand=[card_by_name("Tsuppari")],
                     draw_pile=[card_by_name("Harite")]),
        active_side=Side.A,
    )
    return state


def test_observation_hides_opponent_cards_and_is_immutable():
    state = state_with_hand("Shove", "Oshi", "Tsuki")
    view = observe(state, Side.A)
    assert tuple(c.name for c in view.hand) == ("Shove", "Oshi", "Tsuki")
    assert view.opponent_hand_size == 1
    assert "Tsuppari" not in repr(view)
    assert "Harite" not in repr(view)
    assert not hasattr(view, "opponent_draw_pile")
    assert not hasattr(view, "opponent_hand")
    with pytest.raises(Exception):
        view.position = 2


def test_choice_required_leaves_authoritative_state_unchanged():
    state = state_with_hand("Shove", "Oshi", "Tsuki")
    state.fighter_a.played_this_turn.append(card_by_name("Oshi"))
    before = deepcopy(state)
    with pytest.raises(ChoiceRequired) as exc:
        submit_card_action(state, Side.A, 0)
    assert exc.value.choice_name == "hand_index"
    assert state == before
    assert not state.card_plays
    assert state.fighter_a.plays_remaining == 2
    assert state.fighter_a.hand == before.fighter_a.hand


def test_choice_can_be_retried_and_committed_once():
    state = state_with_hand("Shove", "Oshi", "Tsuki")
    state.fighter_a.played_this_turn.append(card_by_name("Oshi"))
    assert len(legal_actions(state, Side.A)) == 3
    submit_card_action(state, Side.A, 0, choices={"hand_index": 0})
    assert state.card_plays == [(Side.A, "Shove")]
    assert state.fighter_a.cards_played_this_turn == 1
    assert "Tsuki" in [c.name for c in state.fighter_a.hand]
    assert "Oshi" in [c.name for c in state.fighter_a.discard_pile]


def test_other_side_cannot_play_and_invalid_index_is_atomic():
    state = state_with_hand("Oshi")
    before = deepcopy(state)
    assert not legal_actions(state, Side.B)
    with pytest.raises(IllegalPlay):
        submit_card_action(state, Side.B, 0)
    with pytest.raises(IllegalPlay):
        submit_card_action(state, Side.A, 44)
    assert state == before


def test_human_pull_prompts_for_mode_without_mutation():
    state = state_with_hand("Pull")
    before = deepcopy(state)
    with pytest.raises(ChoiceRequired) as exc:
        submit_card_action(state, Side.A, 0)
    assert exc.value.choice_name == "mode"
    assert set(exc.value.options) == {"reversal", "filter"}
    assert state == before


def test_human_read_the_move_prompts_when_removal_is_available():
    from kimarite.temporary import add_temporary
    state = state_with_hand("Read the Move")
    add_temporary(state, Side.B, card_by_name("Pull"), phase="exchange")
    before = deepcopy(state)
    with pytest.raises(ChoiceRequired) as exc:
        submit_card_action(state, Side.A, 0)
    assert exc.value.choice_name == "mode"
    assert set(exc.value.options) == {"remove", "draw"}
    assert state == before
