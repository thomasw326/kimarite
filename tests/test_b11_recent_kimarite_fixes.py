"""B11 agreed finish-condition corrections stay aligned in engine and UI."""
from kimarite.b11_victory_checks import victory_checks
from kimarite.kimarite import kimarite_is_satisfied
from kimarite.catalog import card_by_name
from kimarite.models import BoutState, Card, FighterState, Side, Wrestler
from kimarite.b10_card_info import card_info


def _state(momentum=0, position=0, power=6, opponent_unstable=False, gained=False):
    blank = Card(99903, "Blank")
    a = FighterState(Wrestler("A", 0, 0, 0, blank, blank, blank))
    b = FighterState(Wrestler("B", 0, 0, 0, blank, blank, blank))
    state = BoutState(a, b, momentum=momentum, position=position)
    a.power = power
    b.unstable = opponent_unstable
    a.gained_momentum_this_turn = gained
    return state


def _matches_display(state, name):
    return all(c["met"] for c in victory_checks(state, Side.A, name))


def test_hatakikomi_requires_opponent_unstable():
    for unstable, expected in ((False, False), (True, True)):
        state = _state(momentum=-2, power=6, opponent_unstable=unstable)
        assert kimarite_is_satisfied(state, Side.A, card_by_name("Hatakikomi")) is expected
        assert _matches_display(state, "Hatakikomi") is expected
    assert not kimarite_is_satisfied(_state(momentum=-1, opponent_unstable=True), Side.A, card_by_name("Hatakikomi"))
    assert not kimarite_is_satisfied(_state(momentum=-2, power=5, opponent_unstable=True), Side.A, card_by_name("Hatakikomi"))
    assert "Unstable" in card_info(card_by_name("Hatakikomi"))["description"]


def test_utchari_accepts_minus_three_and_minus_four_only_with_gain():
    for position in (-4, -3, -2):
        for gained in (False, True):
            state = _state(position=position, gained=gained)
            expected = position <= -3 and gained
            assert kimarite_is_satisfied(state, Side.A, card_by_name("Utchari")) is expected
            assert _matches_display(state, "Utchari") is expected


def test_oshitaoshi_requires_forward_position_as_well_as_momentum_and_power():
    for position in (-1, 0, 1, 2):
        state = _state(momentum=2, position=position, power=8)
        expected = position >= 1
        assert kimarite_is_satisfied(state, Side.A, card_by_name("Oshitaoshi")) is expected
        assert _matches_display(state, "Oshitaoshi") is expected
    for momentum, power in ((1, 8), (2, 7)):
        state = _state(momentum=momentum, position=1, power=power)
        assert not kimarite_is_satisfied(state, Side.A, card_by_name("Oshitaoshi"))
    assert "Position" in card_info(card_by_name("Oshitaoshi"))["description"]


def test_abisetaoshi_requires_positive_momentum_without_changing_grip_or_power():
    from kimarite.models import GripState
    for momentum in (0, 1, 2):
        state = _state(momentum=momentum, power=10)
        state.fighter(Side.A).left_grip = GripState.DEEP
        expected = momentum >= 1
        assert kimarite_is_satisfied(state, Side.A, card_by_name("Abisetaoshi")) is expected
        assert _matches_display(state, "Abisetaoshi") is expected
    state = _state(momentum=1, power=10)
    assert not kimarite_is_satisfied(state, Side.A, card_by_name("Abisetaoshi"))
    assert _matches_display(state, "Abisetaoshi") is False
    assert "Momentum" in card_info(card_by_name("Abisetaoshi"))["description"]
