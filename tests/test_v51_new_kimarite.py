"""Direct V5.1 checks for six newly selected Kimarite."""
from kimarite.catalog import card_by_name
from kimarite.effects import EffectContext
from kimarite.kimarite import kimarite_is_satisfied
from kimarite.kimarite_effects import resolve_kimarite_play_effect
from kimarite.models import BoutState, Card, FighterState, GripState, Side, Wrestler


def bout():
    blank = Card(51000, "Test Blank")
    a = Wrestler("A", 2, 2, 2, blank, blank, blank)
    b = Wrestler("B", 2, 2, 2, blank, blank, blank)
    return BoutState(FighterState(a), FighterState(b)), blank


def test_kirikaeshi_needs_power_deficit_hand_advantage_and_successful_reversal():
    s, blank = bout()
    k = card_by_name("Kirikaeshi")
    s.fighter_a.power = 1
    s.fighter_b.power = 4
    s.fighter_a.hand = [blank] * 2
    s.fighter_b.hand = [blank]
    assert not kimarite_is_satisfied(s, Side.A, k)
    s.fighter_a.successful_reversal_this_turn = True
    assert kimarite_is_satisfied(s, Side.A, k)
    s.fighter_b.power = 3
    assert not kimarite_is_satisfied(s, Side.A, k)


def test_okuri_finishes_need_successful_reversal_and_distinct_position_momentum():
    s, _ = bout()
    dashi, taoshi = card_by_name("Okuridashi"), card_by_name("Okuritaoshi")
    s.position = 1
    s.momentum = 1
    assert not kimarite_is_satisfied(s, Side.A, dashi)
    s.fighter_a.successful_reversal_this_turn = True
    assert kimarite_is_satisfied(s, Side.A, dashi)
    assert not kimarite_is_satisfied(s, Side.A, taoshi)
    s.position = 0
    s.momentum = 2
    assert kimarite_is_satisfied(s, Side.A, taoshi)
    assert not kimarite_is_satisfied(s, Side.A, dashi)


def test_sukuinage_needs_no_grip_momentum_two_and_three_extra_hand_cards():
    s, blank = bout()
    k = card_by_name("Sukuinage")
    s.momentum = 2
    s.fighter_a.hand = [blank] * 3
    assert kimarite_is_satisfied(s, Side.A, k)
    s.fighter_a.left_grip = GripState.GRIP
    assert not kimarite_is_satisfied(s, Side.A, k)


def test_utchari_needs_gain_momentum_this_turn_and_position_minus_three():
    s, _ = bout()
    k = card_by_name("Utchari")
    s.position = -3
    assert not kimarite_is_satisfied(s, Side.A, k)
    s.fighter_a.gained_momentum_this_turn = True
    assert kimarite_is_satisfied(s, Side.A, k)
    s.position = -2
    assert not kimarite_is_satisfied(s, Side.A, k)


def test_uwatedashinage_needs_left_grip_momentum_and_five_power_deficit():
    s, _ = bout()
    k = card_by_name("Uwatedashinage")
    s.fighter_a.left_grip = GripState.GRIP
    s.fighter_a.power = 1
    s.fighter_b.power = 6
    s.momentum = 1
    assert kimarite_is_satisfied(s, Side.A, k)
    s.fighter_a.left_grip = GripState.NONE
    assert not kimarite_is_satisfied(s, Side.A, k)


def test_okuri_exchange_choices_have_opposite_tradeoffs():
    s, _ = bout()
    resolve_kimarite_play_effect(s, Side.A, card_by_name("Okuridashi"),
                                 EffectContext(choices={"mode": "position_to_momentum"}))
    assert (s.position, s.momentum) == (-1, 2)
    resolve_kimarite_play_effect(s, Side.A, card_by_name("Okuritaoshi"),
                                 EffectContext(choices={"mode": "momentum_to_position"}))
    assert (s.position, s.momentum) == (1, 1)


def test_new_draw_and_grip_exchange_effects():
    s, blank = bout()
    s.fighter_a.draw_pile = [blank, blank, blank, blank]
    resolve_kimarite_play_effect(s, Side.A, card_by_name("Kirikaeshi"), EffectContext())
    assert len(s.fighter_a.hand) == 1
    resolve_kimarite_play_effect(s, Side.A, card_by_name("Sukuinage"), EffectContext())
    assert len(s.fighter_a.hand) == 2
    s.position = -1
    resolve_kimarite_play_effect(s, Side.A, card_by_name("Utchari"), EffectContext())
    assert len(s.fighter_a.hand) == 3
    s.fighter_a.hand.clear()
    s.fighter_a.draw_pile = [blank]
    resolve_kimarite_play_effect(s, Side.A, card_by_name("Uwatedashinage"),
                                 EffectContext(choices={"discard_for_grip": True, "hand_index": 0}))
    assert s.fighter_a.left_grip is GripState.GRIP
    assert not s.fighter_a.hand


def test_normal_v51_surviving_reversal_sets_event_without_r20_flag():
    from kimarite.temporary import add_temporary, resolve_start_of_turn_temporaries
    s, _ = bout()
    card = card_by_name("Pull")
    assert not s.r20_active
    add_temporary(s, Side.A, card, phase="exchange")
    resolve_start_of_turn_temporaries(s, Side.A)
    assert s.fighter_a.successful_reversal_this_turn
    assert any(event[1] == "Pull" for event in s.reversal_completions)


def test_normal_v51_start_turn_can_win_with_completed_reversal():
    from kimarite.temporary import add_temporary
    from kimarite.turns import start_exchange_turn
    from kimarite.tachiai import compare_tachiai
    s, blank = bout()
    finisher = card_by_name("Okuridashi")
    s.fighter_a.kimarite_zone.append(finisher)
    s.position = 1
    s.momentum = -1  # Surviving Pull flips Momentum to +1.
    s.fighter_a.first_exchange_turn = False
    s.fighter_a.draw_pile = [blank, blank, blank]
    add_temporary(s, Side.A, card_by_name("Pull"), phase="exchange")
    compare = compare_tachiai(s.fighter_a.wrestler, s.fighter_b.wrestler)
    start_exchange_turn(s, Side.A, compare)
    assert s.fighter_a.successful_reversal_this_turn
    assert s.winner is Side.A
    assert s.win_method == "Okuridashi"
