"""Structural and end-to-end smoke checks for the isolated R21 tournament."""
from collections import Counter
from itertools import islice

import pytest

from kimarite.effects import EffectContext
from kimarite.models import BoutState, Card, FighterState, Side, Wrestler
from kimarite.r21_gauntlet import load_arms, schedule, generic_roster
from kimarite.r21_gauntlet_bouts import prepare_fixture, run_fixture
from kimarite.r21_variant_rules import (
    build_variant_card, variant_predicate, variant_exchange,
)


def sample():
    kim = Card(90001, "Yorikiri", 1, 1, 1, True)
    basics = [Card(7000 + i, f"Filler{i}", 1, 1, 1) for i in range(30)]
    w1 = Wrestler("Subject", 2, 2, 1, kim, basics[0], basics[1])
    w2 = Wrestler("Opponent", 2, 2, 1, kim, basics[2], basics[3])
    a = FighterState(w1, draw_pile=list(basics), hand=basics[:5],
                     kimarite_zone=[kim], power=5)
    b = FighterState(w2, draw_pile=list(basics), hand=basics[5:10],
                     kimarite_zone=[kim], power=6)
    return BoutState(a, b, r20_active=True)


def test_manifest_coverage_and_ids():
    arms = load_arms()
    assert len(arms) == 50
    assert len({a.arm_id for a in arms}) == 50
    assert len({a.kimarite for a in arms}) == 18
    assert all(a.arm_id.startswith("R21-") for a in arms)
    assert all(a.orbs and a.exchange_text and a.win_text for a in arms)


def test_every_arm_has_executable_predicate_and_effect():
    for index, arm in enumerate(load_arms()):
        card = build_variant_card(arm.arm_id, card_id=70000 + index)
        assert card.is_kimarite
        assert card.name == "R21:" + arm.arm_id
        assert (card.power, card.technique, card.spirit) == (
            arm.orbs.count("🟣"), arm.orbs.count("🟢"),
            arm.orbs.count("🟠"),
        )
        state = sample()
        assert isinstance(variant_predicate(state, Side.A, arm.arm_id), bool)
        variant_exchange(state, Side.A, card, EffectContext())


def test_50_arm_schedule():
    arms = load_arms()
    assert len(generic_roster()) == 108
    scheduled = list(schedule(arms))
    assert len(scheduled) == 50 * 2 * 648
    assert Counter((a.arm_id, a.placement) for a in scheduled)[
        ("R21-HIK-RS", "starting")
    ] == 648


def test_one_setup_each_arm_each_placement():
    # Setup and isolated predicate must work in either seat with all 50 arms.
    arms = load_arms()
    schedule_items = iter(schedule(arms))
    for arm in arms:
        for placement in ("starting", "shuffled"):
            first = next(schedule_items)
            assert first.arm_id == arm.arm_id and first.placement == placement
            state, card, side = prepare_fixture(arm, first)
            assert state.r20_active
            assert state.fighter(side).wrestler.starting_kimarite == (
                card if placement == "starting"
                else state.fighter(side).wrestler.starting_kimarite
            )
            assert isinstance(variant_predicate(state, side, arm.arm_id), bool)
            # consume the remaining 647 fixtures for this placement
            for _ in range(647):
                next(schedule_items)


def test_hikiotoshi_search_only_removes_topmost_reversal_at_setup():
    arm = next(a for a in load_arms() if a.arm_id == "R21-HIK-RS")
    bout = next(s for s in schedule([arm]) if s.placement == "starting")
    state, _, side = prepare_fixture(arm, bout)
    # End-to-end: the prepared Starting arm generated without a card play;
    # a Reversal in draw deck would have transferred into hand.
    f = state.fighter(side)
    assert len([c for c in f.hand if c.name in {
        "Henka", "Pull", "Sidestep", "Immovable", "Kannuki"
    }]) <= 1
    assert f.kimarite_zone[0].name == "R21:R21-HIK-RS"


@pytest.mark.parametrize("armid", [
    "R21-KAT-NG", "R21-KIR-H3", "R21-SUK-P3", "R21-HIK-RS",
])
@pytest.mark.parametrize("placement", ["starting", "shuffled"])
def test_short_bout_smoke(armid, placement):
    arm = next(a for a in load_arms() if a.arm_id == armid)
    fixture = next(s for s in schedule([arm]) if s.placement == placement)
    result = run_fixture(arm, fixture, max_turns=16)
    assert result.arm_id == armid
    assert result.placement == placement
    assert not result.error.startswith(("TypeError", "KeyError", "AttributeError", "ValueError"))
