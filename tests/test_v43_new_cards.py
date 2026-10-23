"""Focused V4.3 tests: reveal chains, new support cards, and Shitatenage."""
from dataclasses import replace
from kimarite.catalog import card_by_name
from kimarite.effects import EffectContext, resolve_exchange_effect
from kimarite.kimarite import kimarite_is_satisfied
from kimarite.models import BoutState, Card, FighterState, GripState, Side, Wrestler
from kimarite.tachiai import compare_tachiai
from kimarite.tachiai_effects import resolve_prepared_tachiai


def state_with_prepared(prepared, deck=()):
    blank = Card(99999, "Blank")
    a = Wrestler("A", 0, 0, 0, blank, prepared, blank)
    b = Wrestler("B", 0, 0, 0, blank, blank, blank)
    return BoutState(FighterState(a, draw_pile=list(deck)), FighterState(b))


def test_oshi_family_reveal_chain_adds_orbs_and_stops():
    oshi = card_by_name("Oshi")
    tsuki = card_by_name("Tsuki")
    stop = card_by_name("Harite")
    untouched = card_by_name("Belt Slap")
    s = state_with_prepared(oshi, [tsuki, oshi, stop, untouched])
    comparison = compare_tachiai(s.fighter_a.wrestler, s.fighter_b.wrestler)
    resolve_prepared_tachiai(s, comparison)
    assert comparison.power_advantage_a == tsuki.power + oshi.power + stop.power
    assert comparison.spirit_advantage_a == oshi.spirit + tsuki.spirit + oshi.spirit + stop.spirit
    assert [c.name for c in s.fighter_a.discard_pile] == ["Tsuki", "Oshi", "Harite"]
    assert s.fighter_a.draw_pile[0].name == "Belt Slap"


def test_explosive_step_exchange_push_depends_on_preplay_momentum():
    card = card_by_name("Explosive Step — Fumikomi")
    for initial, expected_position in [(-1, 1), (0, 1), (1, 0)]:
        s = state_with_prepared(Card(99998, "Blank"))
        s.momentum = initial
        resolve_exchange_effect(s, Side.A, card, EffectContext())
        assert s.momentum == initial + 1
        assert s.position == expected_position


def test_shove_exchange_no_extra_play():
    s = state_with_prepared(Card(99998, "Blank"))
    resolve_exchange_effect(s, Side.A, card_by_name("Shove"), EffectContext())
    assert s.position == 1
    assert s.fighter_a.plays_remaining == 2


def test_shitatenage_requires_deep_right_grip_and_position():
    s = state_with_prepared(Card(99998, "Blank"))
    card = card_by_name("Shitatenage")
    s.fighter_a.right_grip = GripState.DEEP
    s.momentum = 1
    assert kimarite_is_satisfied(s, Side.A, card)
    s.position = -1
    assert not kimarite_is_satisfied(s, Side.A, card)
    s.position = 0
    s.fighter_a.right_grip = GripState.GRIP
    assert not kimarite_is_satisfied(s, Side.A, card)


def test_shove_tachiai_finishes_at_exactly_three():
    s = state_with_prepared(card_by_name("Shove"))
    s.position = 2
    comparison = compare_tachiai(s.fighter_a.wrestler, s.fighter_b.wrestler)
    resolve_prepared_tachiai(s, comparison)
    assert s.winner is Side.A
    assert s.position == 3
