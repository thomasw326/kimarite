"""Human Kirikaeshi optional conversion must be prompted and applied atomically."""
import pytest

from kimarite.catalog import card_by_name
from kimarite.models import BoutState, FighterState, Side, Wrestler
from kimarite.actions import submit_card_action
from kimarite.effects import ChoiceRequired


def setup():
    blank = card_by_name("Oshi")
    a = FighterState(Wrestler("Player", 3, 0, 1, blank, blank, blank))
    b = FighterState(Wrestler("Opponent", 3, 0, 1, blank, blank, blank))
    a.hand = [card_by_name("Kirikaeshi")]
    a.draw_pile = [card_by_name("Tsuki")]
    a.power = 4
    a.plays_remaining = 2
    state = BoutState(a, b)
    state.active_side = Side.A
    return state


def test_kirikaeshi_human_choice_is_required_and_transactional():
    state = setup()
    with pytest.raises(ChoiceRequired) as exc:
        submit_card_action(state, Side.A, 0)
    assert exc.value.choice_name == "use_optional"
    assert state.fighter_a.power == 4
    assert [c.name for c in state.fighter_a.hand] == ["Kirikaeshi"]
    assert state.fighter_a.plays_remaining == 2


def test_kirikaeshi_optional_yes_converts_and_draws():
    state = setup()
    submit_card_action(state, Side.A, 0, choices={"use_optional": True})
    assert state.fighter_a.power == 3
    assert state.momentum == 1
    assert any(c.name == "Tsuki" for c in state.fighter_a.hand)


def test_kirikaeshi_optional_no_declines():
    state = setup()
    submit_card_action(state, Side.A, 0, choices={"use_optional": False})
    assert state.fighter_a.power == 4
    assert state.momentum == 0
    assert all(c.name != "Tsuki" for c in state.fighter_a.hand)
