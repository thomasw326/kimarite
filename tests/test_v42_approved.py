"""Regression checks for the approved V4.2 local simulation rules."""
from kimarite.catalog import card_by_name
from kimarite.kimarite import kimarite_is_satisfied
from kimarite.models import BoutState, FighterState, GripState, Side, Wrestler
from kimarite.rules import gain_push
from kimarite.effects import EffectContext, resolve_exchange_effect
from kimarite.tachiai import prepared_stats, push_from_power_advantage


def fighter(name):
    w = Wrestler(name, 0, 0, 0, card_by_name("Katasukashi"),
                 card_by_name("Oshi"), card_by_name("Tsuki"))
    return FighterState(w)


def test_approved_orbs_and_uncapped_power():
    assert (card_by_name("Headlong Charge").power, card_by_name("Headlong Charge").technique, card_by_name("Headlong Charge").spirit) == (0, 0, 3)
    a = card_by_name("Abisetaoshi")
    assert (a.power, a.technique, a.spirit) == (3, 0, 0)
    assert (push_from_power_advantage(1), push_from_power_advantage(3),
            push_from_power_advantage(5), push_from_power_advantage(7)) == (1, 1, 2, 3)


def test_tsuridashi_total_grip_three_and_power_six():
    s = BoutState(fighter("A"), fighter("B"))
    s.fighter_a.left_grip = GripState.DEEP
    s.fighter_a.right_grip = GripState.GRIP
    s.fighter_a.power = 6
    assert kimarite_is_satisfied(s, Side.A, card_by_name("Tsuridashi"))
    s.fighter_a.right_grip = GripState.NONE
    assert not kimarite_is_satisfied(s, Side.A, card_by_name("Tsuridashi"))


def test_kotenage_requires_five_cards_in_hand():
    s = BoutState(fighter("A"), fighter("B"), momentum=1)
    s.fighter_a.hand = [card_by_name("Oshi")] * 4
    assert not kimarite_is_satisfied(s, Side.A, card_by_name("Kotenage"))
    s.fighter_a.hand.append(card_by_name("Tsuki"))
    assert kimarite_is_satisfied(s, Side.A, card_by_name("Kotenage"))


def test_gain_left_grip_deepens_and_protects_one_push():
    s = BoutState(fighter("A"), fighter("B"))
    card = card_by_name("Gain Left Grip")
    resolve_exchange_effect(s, Side.A, card, EffectContext())
    assert s.fighter_a.left_grip == GripState.GRIP
    assert len(s.fighter_a.temporary_zone) == 1
    gain_push(s, Side.B, 2)
    assert s.position == -1
    assert not s.fighter_a.temporary_zone
    resolve_exchange_effect(s, Side.A, card, EffectContext())
    assert s.fighter_a.left_grip == GripState.DEEP


def test_approved_kinematic_finishes():
    s = BoutState(fighter("A"), fighter("B"), momentum=-2, position=2)
    s.fighter_a.cards_played_this_turn = 4
    assert kimarite_is_satisfied(s, Side.A, card_by_name("Tsukidashi"))
    s.position = -2
    assert not kimarite_is_satisfied(s, Side.A, card_by_name("Tsukidashi"))
    s.momentum = 2
    assert kimarite_is_satisfied(s, Side.A, card_by_name("Tsukitaoshi"))


def test_regain_balance_conditional_power():
    s = BoutState(fighter("A"), fighter("B"), momentum=-1)
    s.fighter_a.draw_pile = [card_by_name("Oshi")]
    resolve_exchange_effect(s, Side.A, card_by_name("Regain Balance"), EffectContext())
    # Current Regain Balance recovers one Momentum, not two.
    assert s.momentum == 0
    assert s.fighter_a.power == 2
    assert len(s.fighter_a.hand) == 1
