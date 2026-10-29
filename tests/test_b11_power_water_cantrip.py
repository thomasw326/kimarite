"""Power Water Cantrip recovers only one card to hand, bottoms two."""
import pytest

from kimarite.catalog import card_by_name
from kimarite.effects import ChoiceRequired, EffectContext, _power_water_cantrip
from kimarite.models import BoutState, Card, FighterState, Side, Wrestler


def scenario(count=3):
    blank = card_by_name("Oshi")
    a = FighterState(Wrestler("Human", 0, 0, 0, blank, blank, blank))
    b = FighterState(Wrestler("AI", 0, 0, 0, blank, blank, blank))
    a.discard_pile = [card_by_name(n) for n in ["Tsuki", "Shove", "Harite"][:count]]
    a.draw_pile = [card_by_name("Gain Left Grip")]
    a.plays_remaining = 1
    return BoutState(a, b)


def test_one_card_to_hand_two_to_bottom_and_no_bonus_draw():
    state = scenario()
    _power_water_cantrip(state, Side.A, Card(62, "Power Water Cantrip"), EffectContext(choices={"discard_index": 0, "__human__": True}))
    own = state.fighter_a
    assert [c.name for c in own.hand] == ["Tsuki"]
    assert [c.name for c in own.draw_pile] == ["Gain Left Grip", "Harite", "Shove"]
    assert own.discard_pile == []
    assert own.plays_remaining == 2


@pytest.mark.parametrize("count", [0, 1, 2])
def test_fewer_than_three_discards_recycles_without_duplicates(count):
    state = scenario(count)
    before = [c.name for c in state.fighter_a.discard_pile]
    _power_water_cantrip(state, Side.A, Card(62, "Power Water Cantrip"), EffectContext())
    own = state.fighter_a
    moved = [c.name for c in own.hand] + [c.name for c in own.draw_pile[1:]] + [c.name for c in own.discard_pile]
    assert sorted(moved) == sorted(before)
    assert len(own.hand) <= 1


def test_human_must_choose_discard_before_mutation():
    state = scenario()
    with pytest.raises(ChoiceRequired) as exc:
        _power_water_cantrip(state, Side.A, Card(62, "Power Water Cantrip"), EffectContext(choices={"__human__": True}))
    assert exc.value.choice_name == "discard_index"
    assert [c.name for c in state.fighter_a.discard_pile] == ["Tsuki", "Shove", "Harite"]
