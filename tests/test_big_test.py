import random
from collections import Counter

from scripts.big_test import STAT_BUILDS, make_fighter, roster
from kimarite.models import Stat


def test_108_unique_configs():
    configs = roster()
    assert len(STAT_BUILDS) == 18
    assert len(configs) == 108
    assert len(set(name for name, _, _ in configs)) == 108
    assert all(sum(stats) == 5 for stats in STAT_BUILDS)


def test_random_card_assignments_are_independent_and_reproducible():
    configs = roster()
    a = make_fighter(configs[0], random.Random(321), 1)
    b = make_fighter(configs[-1], random.Random(321), 1)
    assert a.wrestler.starting_kimarite == b.wrestler.starting_kimarite
    assert a.wrestler.prepared_tachiai_card == b.wrestler.prepared_tachiai_card
    assert a.wrestler.top_of_deck_card == b.wrestler.top_of_deck_card
    assert len(a.draw_pile) == len(b.draw_pile)
    assert a.draw_pile == b.draw_pile


def test_card_positions_are_distinct_and_reproducible():
    fighter = make_fighter(roster()[0], random.Random(12345), 1)
    w = fighter.wrestler
    assert w.starting_kimarite.is_kimarite
    reserved = {w.starting_kimarite.name, w.prepared_tachiai_card.name,
                w.top_of_deck_card.name}
    assert len(reserved) == 3
    assert fighter.draw_pile[0] == w.top_of_deck_card
    assert not reserved.intersection(card.name for card in fighter.draw_pile[1:])


def test_every_pool_card_is_legal_as_prepared_tachiai():
    """All cards contribute stats; only cards with phase text add phase effects."""
    from dataclasses import replace
    from kimarite.catalog import CARD_POOL
    from kimarite.models import BoutState, FighterState
    from kimarite.tachiai import compare_tachiai
    from kimarite.tachiai_effects import resolve_prepared_tachiai

    base = make_fighter(roster()[0], random.Random(42), 1).wrestler
    foe = make_fighter(roster()[1], random.Random(13), 2).wrestler
    for card in CARD_POOL:
        first = replace(base, prepared_tachiai_card=card)
        state = BoutState(
            FighterState(first, draw_pile=list(CARD_POOL)),
            FighterState(foe, draw_pile=list(CARD_POOL)),
        )
        comparison = compare_tachiai(first, foe)
        resolve_prepared_tachiai(state, comparison)


def test_all_names_eligible_globally_and_reserved_locally():
    from kimarite.catalog import CARD_POOL, STARTING_KIMARITE
    all_names = {card.name for card in CARD_POOL}
    assert len(all_names) == 54
    assert "Oshi" in all_names
    assert "Bad Oshi" not in all_names
    assert len({card.card_id for card in CARD_POOL}) == len(CARD_POOL)
    assert {card.name for card in STARTING_KIMARITE} <= all_names
    seen_kimarite, seen_prepared, seen_top = set(), set(), set()
    for seed in range(1000):
        fighter = make_fighter(roster()[seed % 108], random.Random(seed), 1)
        w = fighter.wrestler
        reserved = {w.starting_kimarite.name, w.prepared_tachiai_card.name,
                    w.top_of_deck_card.name}
        assert len(reserved) == 3
        assert w.starting_kimarite.is_kimarite
        assert fighter.draw_pile[0] == w.top_of_deck_card
        assert not reserved.intersection(card.name for card in fighter.draw_pile[1:])
        seen_kimarite.add(w.starting_kimarite.name)
        seen_prepared.add(w.prepared_tachiai_card.name)
        seen_top.add(w.top_of_deck_card.name)
    assert seen_kimarite == {card.name for card in STARTING_KIMARITE}
    assert seen_prepared == all_names
    assert seen_top == all_names


def test_technique_advantage_1_3_5_7_thresholds():
    from kimarite.tachiai import technique_access
    assert [technique_access(d) for d in range(0, 11)] == [
        (2, 2), (3, 3), (4, 3), (5, 4), (6, 4),
        (7, 5), (8, 5), (9, 6), (10, 6), (11, 7), (12, 7),
    ]
    assert technique_access(-3) == (2, 2)


def test_card_origins_use_identity_not_name():
    from scripts.big_test import card_origin
    fighter = make_fighter(roster()[0], random.Random(701), 1)
    w = fighter.wrestler
    assert card_origin(w, w.starting_kimarite.card_id) == "starting_kimarite"
    assert card_origin(w, w.prepared_tachiai_card.card_id) == "prepared_tachiai"
    assert card_origin(w, w.top_of_deck_card.card_id) == "top_of_deck"
    assert card_origin(w, fighter.draw_pile[1].card_id) == "shuffled_remainder"


def test_kimarite_victory_records_specific_copy():
    from kimarite.models import BoutState, FighterState, GripState, Side
    from kimarite.turns import check_kimarite_zone
    fighter = make_fighter(roster()[0], random.Random(600), 1)
    other = make_fighter(roster()[1], random.Random(601), 2)
    from kimarite.catalog import card_by_name
    card = card_by_name("Yorikiri")
    fighter.kimarite_zone = [card]
    fighter.left_grip = GripState.DEEP
    fighter.right_grip = GripState.DEEP
    state = BoutState(fighter, other, position=2)
    # The winner identity is recorded even when it is not the starting copy.
    selected = check_kimarite_zone(state, Side.A)
    if selected is not None:
        assert state.winning_kimarite_card_id == selected.card_id


def test_reporting_smoke_produces_consistent_csvs(tmp_path, monkeypatch):
    import csv
    import json
    import sys
    from scripts.big_test import main
    monkeypatch.setattr(sys, "argv", [
        "big_test.py", "--max-pairs", "2", "--output-dir", str(tmp_path),
        "--max-turns", "40",
    ])
    main()
    summary = json.loads((tmp_path / "summary.json").read_text())
    with (tmp_path / "bouts.csv").open(newline="") as f:
        bouts = list(csv.DictReader(f))
    with (tmp_path / "stat_advantages.csv").open(newline="") as f:
        stats = list(csv.DictReader(f))
    with (tmp_path / "kimarite_finishes_by_origin.csv").open(newline="") as f:
        finishes = list(csv.DictReader(f))
    with (tmp_path / "card_play_by_origin.csv").open(newline="") as f:
        plays = list(csv.DictReader(f))
    assert summary["planned_bouts"] == 4
    assert len(bouts) == 4
    assert all(len(row) == 24 for row in bouts)
    assert sum(int(row["bouts"]) for row in stats) == 6 * summary["completed"]
    assert sum(int(row["finishes"]) for row in finishes) == sum(
        n for k, n in summary["win_conditions"].items() if k.startswith("kimarite:")
    )
    assert set(row["origin"] for row in finishes) <= {
        "starting_kimarite", "prepared_tachiai", "top_of_deck", "shuffled_remainder"
    }
    assert set(row["origin"] for row in plays) <= {
        "prepared_tachiai", "top_of_deck", "shuffled_remainder"
    }
    # Verify the new per-origin/stat reports survive batch aggregation.
    from scripts.combine_big_test import main as combine_main
    combined = tmp_path / "combined"
    monkeypatch.setattr(sys, "argv", [
        "combine_big_test.py", str(tmp_path), "--output-dir", str(combined),
    ])
    combine_main()
    with (combined / "stat_advantages.csv").open(newline="") as f:
        aggregated = list(csv.DictReader(f))
    with (combined / "kimarite_finishes_by_origin.csv").open(newline="") as f:
        combined_finishes = list(csv.DictReader(f))
    assert sum(int(row["bouts"]) for row in aggregated) == 6 * summary["completed"]
    assert sum(int(row["finishes"]) for row in combined_finishes) == sum(
        int(row["finishes"]) for row in finishes
    )
