"""R20 schedule, catalogue and descriptive-metric contract checks.

Pure structural tests: do not run bouts or consume GitHub Actions minutes.
"""
from collections import Counter
from itertools import islice

import pytest

from kimarite.r20_gauntlet import (
    BoutRecord,
    DEFAULT_OPPONENT_OFFSETS,
    PLACEMENTS,
    fixtures,
    generic_roster,
    load_arms,
    plan_summary,
    schedule,
    summarize_records,
)


def test_manifest_has_all_approved_variants_and_no_missing_orbs():
    arms = load_arms()
    assert len(arms) == 70
    assert len({arm.arm_id for arm in arms}) == 70
    assert len({arm.kimarite for arm in arms}) == 22
    assert {arm.arm_id for arm in arms if arm.kimarite == "Katasukashi"} == {
        "KAT-0", "KAT-1", "KAT-2", "KAT-3"
    }
    assert {arm.orbs for arm in arms if arm.kimarite == "Tsukiotoshi"} == {"🟣🟢🟠"}
    assert {arm.exchange_text for arm in arms if arm.kimarite == "Tsukiotoshi"} == {
        "Gain +1 Play this turn"
    }


def test_generic_roster_has_all_stat_build_priority_order_combinations():
    roster = generic_roster()
    assert len(roster) == 108
    assert len({(r.stats, r.priorities) for r in roster}) == 108
    assert len({r.stats for r in roster}) == 18
    assert len({r.priorities for r in roster}) == 6
    assert all(sum(r.stats) == 5 for r in roster)


def test_fixtures_cover_each_subject_with_distinct_opponents():
    ff = fixtures()
    assert len(ff) == 108 * 6
    assert all(f.subject_index != f.opponent_index for f in ff)
    assert all(0 <= f.opponent_index < 108 for f in ff)
    each = Counter(f.subject_index for f in ff)
    opponent_counts = Counter(f.opponent_index for f in ff)
    assert set(each.values()) == {6}
    assert set(opponent_counts.values()) == {6}


def test_single_seat_per_fixture_with_balanced_assignment():
    arm = load_arms()[0]
    bouts = list(schedule([arm]))
    # One bout per fixture per placement; never repeat the reversed seat.
    assert len(bouts) == 108 * 6 * 2
    assert len({
        (b.arm_id, b.placement, b.fixture_id) for b in bouts
    }) == len(bouts)
    for placement in PLACEMENTS:
        subset = [b for b in bouts if b.placement == placement]
        assert len(subset) == 648
        assert Counter(b.subject_seat for b in subset) == {"A": 324, "B": 324}
        # Each generic wrestler has three Side A and three Side B opponents.
        by_subject = {}
        for b in subset:
            by_subject.setdefault(b.subject_index, []).append(b.subject_seat)
        assert len(by_subject) == 108
        assert all(Counter(seats) == {"A": 3, "B": 3}
                   for seats in by_subject.values())
    # Same seed and chosen seat in both Starting and Shuffled conditions.
    for start, shuffled in zip(bouts[:648], bouts[648:]):
        assert (start.fixture_id, start.subject_seat, start.seed) == (
            shuffled.fixture_id, shuffled.subject_seat, shuffled.seed
        )


def test_arm_comparisons_get_exact_same_fixtures():
    arms = load_arms()
    a = next(a for a in arms if a.arm_id == "OKD-1")
    b = next(a for a in arms if a.arm_id == "OKD-3")
    left = [
        (x.placement, x.fixture_id, x.subject_index, x.opponent_index, x.subject_seat, x.seed)
        for x in islice(schedule([a]), 0, 20)
    ]
    right = [
        (x.placement, x.fixture_id, x.subject_index, x.opponent_index, x.subject_seat, x.seed)
        for x in islice(schedule([b]), 0, 20)
    ]
    assert left == right


def test_complete_schedule_count():
    arms = load_arms()
    plan = plan_summary(arms, len(DEFAULT_OPPONENT_OFFSETS))
    assert plan["planned_bouts"] == 90720
    assert plan["seat_orientations_per_fixture"] == 1
    assert plan["bouts_per_arm_per_placement"] == 648
    assert list(PLACEMENTS) == ["starting", "shuffled"]


def test_invalid_opponent_offsets_refused():
    with pytest.raises(ValueError):
        fixtures(opponent_offsets=(0,))
    with pytest.raises(ValueError):
        fixtures(opponent_offsets=(1, 1))
    with pytest.raises(ValueError):
        fixtures(opponent_offsets=(108,))


def test_summary_keeps_wins_and_actual_finishes_separate():
    records = [
        BoutRecord("HIK-3", "starting", "A", True, True, False, False, True),
        BoutRecord("HIK-3", "starting", "B", True, True, True, True, True),
        BoutRecord("HIK-3", "starting", "A", True, False, False, True, True),
        BoutRecord("HIK-3", "starting", "B", False, error="timeout"),
    ]
    summary, = summarize_records(records)
    assert summary["scheduled"] == 4
    assert summary["completed"] == 3
    assert summary["incomplete"] == 1
    assert summary["wins"] == 2
    assert summary["kimarite_finishes"] == 1
    assert summary["seat_A"] == summary["seat_B"] == 2
    assert summary["win_rate"] == 0.666667
    assert summary["kimarite_completion_rate"] == 0.333333
    assert summary["completion_given_availability"] == 0.333333


def test_an_incomplete_win_or_nonwinning_finish_is_invalid():
    with pytest.raises(ValueError):
        summarize_records([
            BoutRecord("HIK-3", "starting", "A", False, subject_won=True)
        ])
    with pytest.raises(ValueError):
        summarize_records([
            BoutRecord("HIK-3", "shuffled", "B", True,
                       subject_won=False, finished_by_tested_kimarite=True)
        ])
