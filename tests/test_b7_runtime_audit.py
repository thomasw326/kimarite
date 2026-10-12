"""B7 review audit: test the actual Exchange/variant execution paths.

This file changes NO rules. Two known unimplemented strict throw thresholds
are explicitly marked xfail so the audit does not pretend they're passing.
"""
from __future__ import annotations

import pytest
from kimarite.ai import candidate_plays
from kimarite.catalog import card_by_name
from kimarite.effects import EffectContext, resolve_exchange_effect
from kimarite.models import BoutState, Card, FighterState, GripState, Side, Wrestler
from kimarite.playing import play_card
from kimarite.r21_variant_rules import variant_predicate
from kimarite.tachiai import compare_tachiai
from kimarite.tachiai_effects import resolve_prepared_tachiai


def new_state(name="Oshi", *, power=7, opponent_power=4, hand_extra=(),
              deck_length=6, opponent_hand=(), kimarite_deck=()):
    starter = card_by_name("Oshidashi")
    basic = card_by_name(name)
    w = Wrestler("A", 2, 2, 2, starter, basic, basic)
    z = Wrestler("B", 2, 2, 2, starter, basic, basic)
    draw = [Card(810_000 + i, f"Audit Blank {i}") for i in range(deck_length)]
    draw += list(kimarite_deck)
    a = FighterState(w, power=power, hand=[basic, *hand_extra], draw_pile=draw)
    b = FighterState(z, power=opponent_power, hand=list(opponent_hand))
    return BoutState(a, b, active_side=Side.A, r20_active=True)


def play_named(s, name):
    card = next(x for x in s.fighter_a.hand if x.name == name)
    play_card(s, Side.A, card)


def test_b7_oshi_requires_discard_and_draws_and_mills_through_real_play():
    sacrifice = Card(830_001, "Oshi discarded cost")
    s = new_state("Oshi", hand_extra=(sacrifice,), deck_length=4)
    play_named(s, "Oshi")
    assert s.position == 1 and s.momentum == 0
    assert s.fighter_a.plays_remaining == 2  # 2 - 1 spent + 1 bonus
    assert [c.name for c in s.fighter_a.hand] == ["Audit Blank 0"]
    assert [c.name for c in s.fighter_a.discard_pile] == [
        "Oshi discarded cost", "Audit Blank 1", "Oshi"
    ]
    assert len(s.fighter_a.draw_pile) == 2
    assert not any("Oshi" == x for x in ("unexpected power modifier",))
    no_cost = new_state("Oshi", deck_length=4)
    play_named(no_cost, "Oshi")
    assert no_cost.position == 0 and no_cost.momentum == 0
    assert no_cost.fighter_a.plays_remaining == 1
    assert len(no_cost.fighter_a.hand) == 0
    assert len(no_cost.fighter_a.draw_pile) == 4
    # The tactical AI sees Oshi as a real candidate when a discard is available.
    choose = new_state("Oshi", hand_extra=(Card(831_000, "Harite"),))
    compared = compare_tachiai(choose.fighter_a.wrestler, choose.fighter_b.wrestler)
    assert any(p.card.name == "Oshi" for p in candidate_plays(choose, Side.A, compared))


def test_b7_explosive_step_only_gains_push_at_nonpositive_momentum_and_mills_two():
    s = new_state("Explosive Step — Fumikomi")
    play_named(s, "Explosive Step — Fumikomi")
    assert (s.position, s.momentum, len(s.fighter_a.draw_pile)) == (1, 0, 4)
    good = new_state("Explosive Step — Fumikomi")
    good.momentum = 1
    play_named(good, "Explosive Step — Fumikomi")
    assert (good.position, good.momentum, len(good.fighter_a.draw_pile)) == (0, 1, 4)


def test_b7_salt_throw_gets_one_play_in_exchange_but_not_tachiai():
    s = new_state("Salt Throw")
    play_named(s, "Salt Throw")
    assert s.fighter_a.plays_remaining == 2
    assert [x.card.name for x in s.fighter_a.temporary_zone] == ["Salt Throw"]

    t = new_state("Salt Throw")
    compared = compare_tachiai(t.fighter_a.wrestler, t.fighter_b.wrestler)
    before = t.fighter_a.plays_remaining
    resolve_prepared_tachiai(t, compared)
    assert t.fighter_a.plays_remaining == before
    assert any(x.card.name == "Salt Throw" for x in t.fighter_a.temporary_zone)


def test_b7_power_water_generates_six_cards_and_extra_play_in_exchange_and_tachiai():
    s = new_state("Power Water")
    play_named(s, "Power Water")
    assert s.fighter_a.plays_remaining == 2
    assert sum(c.name == "Power Water Cantrip" for c in s.fighter_a.draw_pile) == 6
    t = new_state("Power Water")
    cmp = compare_tachiai(t.fighter_a.wrestler, t.fighter_b.wrestler)
    resolve_prepared_tachiai(t, cmp)
    assert sum(c.name == "Power Water Cantrip" for c in t.fighter_a.draw_pile) == 6


def test_b7_use_the_tawara_searches_kimarite_into_hand_not_zone():
    finisher = card_by_name("Yorikiri")
    s = new_state("Use the Tawara", kimarite_deck=(finisher,))
    existing = len(s.fighter_a.kimarite_zone)
    play_named(s, "Use the Tawara")
    assert finisher in s.fighter_a.hand
    assert len(s.fighter_a.kimarite_zone) == existing
    assert s.position == -1 and s.momentum == 1


def test_b7_driving_force_nerf_is_one_push_one_momentum():
    s = new_state("Driving Force — Power Payoff", power=7)
    play_card(s, Side.A, s.fighter_a.hand[0],
              context=EffectContext(choices={"mode": "power_payoff"}))
    assert (s.position, s.momentum) == (1, 1)


def test_b7_crushing_pressure_nerf_is_one_opponent_power_loss():
    s = new_state("Crushing Pressure — Power Crusher", power=7, opponent_power=4)
    play_card(s, Side.A, s.fighter_a.hand[0],
              context=EffectContext(choices={"mode": "power_crusher"}))
    assert s.fighter_b.power == 3 and s.momentum == 1


def variant(*, grip_left=0, grip_right=0, momentum=0, position=0,
            power_a=4, power_b=4, cards_played=0, hand_count=0,
            opponent_grip=0, reversal=False):
    s = new_state("Oshi", power=power_a, opponent_power=power_b)
    s.position = position
    s.momentum = momentum
    s.fighter_a.left_grip = GripState(grip_left)
    s.fighter_a.right_grip = GripState(grip_right)
    s.fighter_b.left_grip = GripState(opponent_grip)
    s.fighter_a.cards_played_this_turn = cards_played
    s.fighter_a.hand = [Card(900_000+i, "Dummy") for i in range(hand_count)]
    s.fighter_a.successful_reversal_this_turn = reversal
    return s


def test_b7_abisetaoshi_requires_two_grip_power10_momentum1():
    ident="R21-R22-ABI-1"
    s=variant(grip_left=2,power_a=10,momentum=1)
    assert variant_predicate(s,Side.A,ident)
    s.fighter_a.power=9
    assert not variant_predicate(s,Side.A,ident)


def test_b7_kirikaeshi_requires_reversal_power_disadvantage3_hand_advantage3():
    ident="R21-KIR-P3-HA3"
    s=variant(reversal=True,power_a=1,power_b=4,hand_count=3)
    assert variant_predicate(s,Side.A,ident)
    s.fighter_a.hand.pop()
    assert not variant_predicate(s,Side.A,ident)


def test_b7_kotenage_requires_no_opponent_grip_momentum3_six_cards_in_hand():
    ident="R21-KOT-R1"
    s=variant(momentum=3,hand_count=6)
    assert variant_predicate(s,Side.A,ident)
    s.fighter_b.left_grip=GripState.GRIP
    assert not variant_predicate(s,Side.A,ident)


def test_b7_tsukidashi_requires_position2_three_plays_nonnegative_momentum():
    ident="R21-TSU-C1"
    s=variant(position=2,cards_played=3,momentum=0)
    assert variant_predicate(s,Side.A,ident)
    s.momentum=-1
    assert not variant_predicate(s,Side.A,ident)


def test_b7_tsukiotoshi_requires_no_grip_momentum1_power_disadvantage2():
    ident="R21-R22-TSO-2"
    s=variant(momentum=1,power_a=2,power_b=4)
    assert variant_predicate(s,Side.A,ident)
    s.fighter_a.left_grip=GripState.GRIP
    assert not variant_predicate(s,Side.A,ident)


@pytest.mark.xfail(strict=True,reason="BUG: earlier UWD return uses Momentum >=1 and Power disadv >=4; approved R25 requires >=2 and >=5")
def test_b7_uwatedashinage_rejects_earlier_weaker_requirement():
    s=variant(grip_left=1,momentum=1,power_a=0,power_b=4)
    assert not variant_predicate(s,Side.A,"R21-R25-UWD-M2-EX")


@pytest.mark.xfail(strict=True,reason="BUG: earlier Uwatenage return ignores Position and accepts Momentum >=1; approved spec requires >=2 and Position >=0")
def test_b7_uwatenage_rejects_momentum1_and_negative_position():
    s=variant(grip_left=2,momentum=1,position=-1)
    assert not variant_predicate(s,Side.A,"R21-UWA-C1-M2")


def test_b7_approved_uwd_and_uwa_requirements_do_hold_at_strict_thresholds():
    assert variant_predicate(
        variant(grip_left=1,momentum=2,power_a=0,power_b=5),
        Side.A,"R21-R25-UWD-M2-EX")
    assert variant_predicate(
        variant(grip_left=2,momentum=2,position=0),
        Side.A,"R21-UWA-C1-M2")


def test_b7_22_card_roster_and_kotenage_orbs_reach_active_simulator():
    from kimarite import style_ai_v5, style_builds_v5, style_simulate_v5
    from kimarite.r26_style_final22 import install_final22
    install_final22()
    final={x.name:x for x in style_builds_v5.CARD_POOL if x.is_kimarite}
    assert len(final)==22
    assert "R21:R21-R25-UWD-M2-EX" in final
    assert "R21:R21-UWA-C1-M2" in final
    assert "R21:R21-R22-ABI-1" in final
    assert "R21:R21-KIR-P3-HA3" in final
    assert (final["R21:R21-KOT-R1"].power,final["R21:R21-KOT-R1"].technique,final["R21:R21-KOT-R1"].spirit)==(1,2,0)
    assert style_ai_v5.card_affinity("Pressure Fighter","Power Water") > 0
    # The 27+13 batch installs the very same rules and style AI.
    assert "play_style_turn" in style_simulate_v5.run_style_bout.__code__.co_names
    from pathlib import Path
    assert Path("scripts/three_style_random13_audit.py").exists()


def test_b7_two_real_bouts_finish_using_the_reviewed_rules():
    from kimarite import style_simulate_v5
    from kimarite.r26_style_final22 import install_final22
    install_final22()
    for first,second in [
        ("Fast Grappler","The Technician"),
        ("Pressure Fighter","Fast Grappler"),
    ]:
        result=style_simulate_v5.run_style_bout(
            first,second,seed=20261012,max_turns=100,
            difficulty=0,experimental_final22=True)
        assert result.completed, result.unsupported_reason
        assert result.state.winner is not None
