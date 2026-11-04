"""Regression coverage for V5.1 finishers under currently approved B11 rules.

The original V5.1 experiments used reversal and extra-mode prerequisites that
were explicitly superseded. Verify the current runtime, not the retired arms.
"""
from kimarite.catalog import card_by_name
from kimarite.effects import EffectContext, resolve_exchange_effect
from kimarite.kimarite import kimarite_is_satisfied
from kimarite.kimarite_effects import resolve_kimarite_play_effect
from kimarite.models import BoutState, Card, FighterState, GripState, Side, Wrestler


def bout():
    blank = Card(51000, "Test Blank")
    a = Wrestler("A", 2, 2, 2, blank, blank, blank)
    b = Wrestler("B", 2, 2, 2, blank, blank, blank)
    return BoutState(FighterState(a), FighterState(b)), blank


def test_kirikaeshi_reverses_power_deficit_against_unstable_opponent():
    s, _ = bout()
    k = card_by_name("Kirikaeshi")
    s.fighter_a.power, s.fighter_b.power = 1, 4
    s.momentum = 2
    assert not kimarite_is_satisfied(s, Side.A, k)
    s.fighter_b.unstable = True
    assert kimarite_is_satisfied(s, Side.A, k)
    s.fighter_a.unstable = True
    assert not kimarite_is_satisfied(s, Side.A, k)
    s.fighter_a.unstable = False
    s.fighter_b.power = 3
    assert not kimarite_is_satisfied(s, Side.A, k)


def test_generated_okuri_finishes_use_distinct_position_and_power():
    s, _ = bout()
    dashi, taoshi = card_by_name("Okuridashi"), card_by_name("Okuritaoshi")
    s.position, s.momentum = 2, 1
    assert kimarite_is_satisfied(s, Side.A, dashi)
    assert not kimarite_is_satisfied(s, Side.A, taoshi)
    s.position = 0
    s.fighter_a.power = 8
    assert kimarite_is_satisfied(s, Side.A, taoshi)
    assert not kimarite_is_satisfied(s, Side.A, dashi)


def test_sukuinage_requires_no_grip_momentum_two_and_four_extra_hand_cards():
    s, blank = bout()
    k = card_by_name("Sukuinage")
    s.momentum = 2
    s.fighter_a.hand = [blank] * 4
    assert kimarite_is_satisfied(s, Side.A, k)
    s.fighter_b.hand.append(blank)
    assert not kimarite_is_satisfied(s, Side.A, k)
    s.fighter_b.hand.clear()
    s.fighter_a.left_grip = GripState.GRIP
    assert not kimarite_is_satisfied(s, Side.A, k)


def test_utchari_requires_gaining_momentum_at_position_minus_four():
    s, _ = bout()
    k = card_by_name("Utchari")
    s.position = -3
    assert not kimarite_is_satisfied(s, Side.A, k)
    s.fighter_a.gained_momentum_this_turn = True
    assert not kimarite_is_satisfied(s, Side.A, k)
    s.position = -4
    assert kimarite_is_satisfied(s, Side.A, k)
    s.position = -2
    assert not kimarite_is_satisfied(s, Side.A, k)


def test_uwatedashinage_needs_left_grip_momentum_and_five_power_deficit():
    s, _ = bout()
    k = card_by_name("Uwatedashinage")
    s.fighter_a.left_grip = GripState.GRIP
    s.fighter_a.power, s.fighter_b.power = 1, 6
    s.momentum = 1
    assert kimarite_is_satisfied(s, Side.A, k)
    s.fighter_a.left_grip = GripState.NONE
    assert not kimarite_is_satisfied(s, Side.A, k)


def test_generated_okuri_kimarite_have_no_exchange_bonus():
    s, _ = bout()
    for name in ("Okuridashi", "Okuritaoshi"):
        resolve_kimarite_play_effect(
            s, Side.A, card_by_name(name),
            EffectContext(choices={"mode": "position_to_momentum"}),
        )
    assert (s.position, s.momentum) == (0, 0)


def test_b11_new_finisher_exchange_effects():
    s, blank = bout()
    s.fighter_a.power = 5
    s.fighter_a.draw_pile = [blank] * 7
    resolve_kimarite_play_effect(
        s, Side.A, card_by_name("Kirikaeshi"),
        EffectContext(choices={"use_optional": True}),
    )
    assert len(s.fighter_a.hand) == 1
    assert s.fighter_a.power == 4 and s.momentum == 1
    resolve_kimarite_play_effect(s, Side.A, card_by_name("Sukuinage"), EffectContext())
    assert len(s.fighter_a.hand) == 2
    s.position = -1
    resolve_kimarite_play_effect(s, Side.A, card_by_name("Utchari"), EffectContext())
    assert len(s.fighter_a.hand) == 3
    s.fighter_a.hand.clear()
    s.fighter_a.draw_pile = [blank]
    resolve_kimarite_play_effect(
        s, Side.A, card_by_name("Uwatedashinage"),
        EffectContext(choices={"discard_for_grip": True, "hand_index": 0}),
    )
    assert s.fighter_a.left_grip is GripState.GRIP
    assert not s.fighter_a.hand


def test_normal_immmovable_completed_temporary_records_reversal():
    from kimarite.temporary import add_temporary, resolve_start_of_turn_temporaries
    s, _ = bout()
    assert not s.r20_active
    add_temporary(s, Side.A, card_by_name("Immovable"), phase="exchange")
    resolve_start_of_turn_temporaries(s, Side.A)
    assert s.fighter_a.successful_reversal_this_turn
    assert any(event[1] == "Immovable" for event in s.reversal_completions)


def test_generated_okuridashi_can_win_at_start_of_turn_without_reversal():
    from kimarite.turns import start_exchange_turn
    from kimarite.tachiai import compare_tachiai
    s, blank = bout()
    s.fighter_a.kimarite_zone.append(card_by_name("Okuridashi"))
    s.position = 2
    s.momentum = 1
    s.fighter_a.first_exchange_turn = False
    s.fighter_a.draw_pile = [blank, blank, blank]
    comparison = compare_tachiai(s.fighter_a.wrestler, s.fighter_b.wrestler)
    start_exchange_turn(s, Side.A, comparison)
    assert s.winner is Side.A
    assert s.win_method == "Okuridashi"
