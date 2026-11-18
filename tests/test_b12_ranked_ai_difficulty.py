"""B12 ranked NPC difficulty without changing the existing human match.

Only NPC-vs-NPC play changes. Run all cards through the real effects engine;
never invent a match winner from the pyramid or a win probability.
"""
from collections import Counter
from copy import deepcopy
import json

import pytest

from kimarite.affinity_v5 import affinity
from kimarite.b12_ai_day import ai_deck_names, build_ai_fighter, match_seed, simulate_ai_bout
from kimarite.b12_difficulty import (
    MAX_CARD_SWAPS, ai_difficulty, base_difficulty, hidden_variance,
    pyramid_tier, tuned_base_cards, tuned_stats,
)
from kimarite.b12_division_roster import load_formats, make_roster, validate_world
from kimarite.b12_league import PLAYER, banzuke, new_basho, next_opponents, plan_block
from kimarite.styles_v5 import STYLES


@pytest.mark.parametrize("rank,tier,base", [
    (1, 1, 8), (2, 2, 7), (3, 2, 7), (4, 3, 6),
    (6, 3, 6), (7, 4, 5), (10, 4, 5), (11, 5, 4),
    (15, 5, 4), (16, 6, 3), (21, 6, 3), (22, 7, 2),
    (28, 7, 2), (29, 8, 1), (36, 8, 1), (37, 9, 0),
    (41, 9, 0), (42, 9, 0),
])
def test_triangular_pyramid_exact_rank_groups(rank, tier, base):
    assert pyramid_tier(rank) == tier
    assert base_difficulty(rank) == base


@pytest.mark.parametrize("rank", [None, 0, -2, 43, "1", 1.0, True])
def test_pyramid_rejects_invalid_ranks(rank):
    with pytest.raises(ValueError):
        pyramid_tier(rank)


def test_hidden_modifiers_stable_identical_identity_across_rank_changes_and_saves():
    roster = make_roster(20261117, "Player Rikishi")
    validate_world(roster)
    a = json.loads(json.dumps(roster, ensure_ascii=False))
    assert a == roster
    seen = Counter()
    for w in roster["wrestlers"]:
        sid = w["wrestler_id"]
        modifier = hidden_variance(roster["seed"], sid)
        seen[modifier] += 1
        assert -2 <= modifier <= 2
        if w["rank"] is None:
            continue
        assert ai_difficulty(roster["seed"], sid, w["rank"]) == (
            base_difficulty(w["rank"]) + modifier
        )
        # The identity modifier does NOT reroll when this wrestler moves.
        for new_rank in (1, 2, 11, 25, 42):
            assert ai_difficulty(roster["seed"], sid, new_rank) - base_difficulty(new_rank) == modifier
    assert set(seen) == {-2, -1, 0, 1, 2}
    assert sum(seen.values()) == 60
    assert all("difficulty" not in w and "variance" not in w for w in roster["wrestlers"])
    assert all("difficulty" not in row for row in banzuke(new_basho(roster)))


@pytest.mark.parametrize("bad_seed,bad_id", [(True, "ai-01"), ("2", "ai-01"),
                                                (33, "player"), (33, ""), (33, None)])
def test_private_modifier_rejects_invalid_identity(bad_seed, bad_id):
    with pytest.raises(ValueError):
        hidden_variance(bad_seed, bad_id)


def test_base_tuning_keeps_all_60_frameworks_unique_and_all_reward_origins():
    altered_positive = 0
    altered_negative = 0
    for framework in load_formats():
        originals = framework["base"]
        reward = framework["duplicates"]
        baseline_kimarite = {
            n for n in originals if n in reward or n == framework["starting_kimarite"]
        }
        assert tuned_base_cards(framework, 0) == originals
        for difficulty in (-2, -1, 1, 2, 3, 5, 8, 10):
            new = tuned_base_cards(framework, difficulty)
            assert len(new) == 28 == len(set(new))
            assert set(reward) <= set(new)
            assert framework["starting_kimarite"] in new
            assert baseline_kimarite <= set(new)
            removed = set(originals) - set(new)
            added = set(new) - set(originals)
            assert len(removed) == len(added)
            assert len(added) <= min(MAX_CARD_SWAPS, (abs(difficulty)+1)//2)
            old_affinity = sum(affinity(framework["style_proxy"], n) for n in originals)
            new_affinity = sum(affinity(framework["style_proxy"], n) for n in new)
            if difficulty > 0:
                assert new_affinity >= old_affinity
                altered_positive += bool(added)
            else:
                assert new_affinity <= old_affinity
                altered_negative += bool(added)
            physical = ai_deck_names(framework, 15, difficulty=difficulty)
            assert len(physical) == 40
            assert Counter(physical) == Counter(new + reward)
        assert len(framework["base"]) == 28
    assert altered_positive > 30
    assert altered_negative > 30


@pytest.mark.parametrize("difficulty", [None, "3", 1.5, True])
def test_tuning_invalid_difficulty_rejected(difficulty):
    f = load_formats()[0]
    with pytest.raises(ValueError):
        tuned_base_cards(f, difficulty)


def test_stats_use_existing_seven_step_stat_boosts_only_for_npc_mode():
    f = load_formats()[0]
    profile = STYLES[f["style_proxy"]]
    assert tuned_stats(profile, -2) == profile.stats
    assert tuned_stats(profile, 0) == profile.stats
    assert sum(tuned_stats(profile, 8)) == sum(profile.stats) + 4
    assert sum(tuned_stats(profile, 10)) == sum(profile.stats) + 4
    assert all(a >= b for a, b in zip(tuned_stats(profile, 10), profile.stats))


@pytest.mark.parametrize("rank", [1, 2, 4, 11, 26, 37, 42])
def test_ranked_npc_fighter_changes_deck_and_stats_but_default_player_opponent_does_not(rank):
    f = load_formats()[7]
    w = {"id":"ai-08", "name":"Opponent Name", "style":f["style_proxy"],
         "format_id":f["id"], "rank":rank}
    difficulty = ai_difficulty(151, w["id"], rank)
    baseline = build_ai_fighter(w, f, 203, 3)
    npc = build_ai_fighter(w, f, 203, 3, difficulty=difficulty)
    repeat = build_ai_fighter(w, f, 203, 3, difficulty=difficulty)
    assert (npc.wrestler.base_power, npc.wrestler.base_technique,
            npc.wrestler.base_spirit) == tuned_stats(STYLES[w["style"]], difficulty)
    assert (baseline.wrestler.base_power, baseline.wrestler.base_technique,
            baseline.wrestler.base_spirit) == STYLES[w["style"]].stats
    assert baseline.wrestler.starting_kimarite.name == npc.wrestler.starting_kimarite.name
    assert npc.wrestler.starting_kimarite.name == repeat.wrestler.starting_kimarite.name
    assert [c.name for c in npc.draw_pile] == [c.name for c in repeat.draw_pile]
    assert len(npc.draw_pile) + len(npc.kimarite_zone) + 1 == 31
    # Old player-opponent deck remains exactly the established 28+win copies.
    assert ai_deck_names(f, 3) == f["base"] + f["duplicates"][:3]


def test_actual_ai_bout_uses_pyramid_and_only_full_gameplay_decides_winner(monkeypatch):
    import kimarite.b12_ai_day as day
    world = make_roster(144, "Player")
    league = new_basho(world)
    rows = {w["rank"]: w for w in league["wrestlers"] if w["id"] != PLAYER}
    left, right = rows[1], rows[40]
    f = {x["id"]: x for x in load_formats()}
    captured = []
    original = day.build_ai_fighter
    def record(*args, **kwargs):
        captured.append((args[0]["rank"], kwargs.get("difficulty")))
        return original(*args, **kwargs)
    monkeypatch.setattr(day, "build_ai_fighter", record)
    bout = simulate_ai_bout(left, right, f, master_seed=world["seed"],
                           basho=0, day=0)
    assert captured == [
        (1, ai_difficulty(world["seed"], left["id"], 1)),
        (40, ai_difficulty(world["seed"], right["id"], 40)),
    ]
    assert bout["winner"] in {left["id"], right["id"]}
    assert bout["method"] and bout["turns"] >= 0
    assert bout["deck_size_a"] == bout["deck_size_b"] == 28
    assert "difficulty" not in bout and "variance" not in bout


def test_adaptive_player_opponent_preview_still_uses_live_record_not_hidden_pyramid():
    roster = make_roster(171, "Player")
    league = new_basho(roster)
    original = deepcopy(league)
    opponents = plan_block(league)
    assert len(opponents) == 3
    assert all("difficulty" not in o and "variance" not in o for o in opponents)
    assert league["wrestlers"] == original["wrestlers"]
    assert next_opponents(league) == opponents
