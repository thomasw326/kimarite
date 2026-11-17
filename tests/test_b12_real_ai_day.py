"""Live-rules B12 AI-vs-AI days, without statistical/fake match winners."""
from copy import deepcopy
import json

import pytest

from kimarite.b12_ai_day import (
    ai_deck_names, build_ai_fighter, commit_real_ai_matchday,
    match_seed, simulate_ai_bout,
)
from kimarite.b12_division_roster import load_formats, make_roster
from kimarite.b12_league import PLAYER, banzuke, new_basho, next_day_matches
from scripts.b12_60_big_test import load_designs, make_fighter


def start_day(seed=337, player="Player"):
    roster = make_roster(seed, player)
    league = new_basho(roster)
    pairs = next_day_matches(league)
    return roster, league, pairs


def test_deck_starts_28_and_gains_exactly_one_physical_duplicate_per_win():
    f = load_formats()[0]
    assert len(ai_deck_names(f, 0)) == 28
    assert ai_deck_names(f, 0) == f["base"]
    for won in (1, 4, 7, 12, 15):
        expected = f["base"] + f["duplicates"][:min(12, won)]
        actual = ai_deck_names(f, won)
        assert actual == expected
        assert len(actual) == 28 + min(12, won)
    with pytest.raises(ValueError):
        ai_deck_names(f, -1)


@pytest.mark.parametrize("prior_wins", [0, 1, 6, 12])
def test_ai_fighter_matches_existing_b12_full_simulation_builder(prior_wins):
    # Same B12 60-format source, same opening roles and card order as big test
    # when an equivalent physical deck and seed are provided.
    ours_format = load_formats()[22]
    big_entry = next(f for f in load_designs("max40") if f["id"] == ours_format["id"])
    big_entry = dict(big_entry, cards=ai_deck_names(ours_format, prior_wins))
    wrestler = {"id": "ai-23", "name": "Example Shikona", "style": ours_format["style_proxy"],
                "rank": 18, "format_id": ours_format["id"]}
    actual = build_ai_fighter(wrestler, ours_format, 777, prior_wins)
    expected, _ = make_fighter(big_entry, 777, 18)
    assert (actual.wrestler.base_power, actual.wrestler.base_technique,
            actual.wrestler.base_spirit) == (
            expected.wrestler.base_power, expected.wrestler.base_technique,
            expected.wrestler.base_spirit)
    assert actual.wrestler.starting_kimarite.name == expected.wrestler.starting_kimarite.name
    assert actual.wrestler.prepared_tachiai_card.name == expected.wrestler.prepared_tachiai_card.name
    assert actual.wrestler.top_of_deck_card.name == expected.wrestler.top_of_deck_card.name
    assert [c.name for c in actual.draw_pile] == [c.name for c in expected.draw_pile]
    assert len([*actual.draw_pile, *actual.kimarite_zone,
                actual.wrestler.prepared_tachiai_card]) == 28 + min(12, prior_wins)
    physical = [*actual.draw_pile, *actual.kimarite_zone, actual.wrestler.prepared_tachiai_card]
    assert len({id(card) for card in physical}) == len(physical)


def test_stable_match_seed_varies_with_day_basho_and_format():
    a = match_seed(3, 0, 4, "ai-01", "ai-05", "01")
    assert a == match_seed(3, 0, 4, "ai-01", "ai-05", "01")
    assert len({a, match_seed(3, 0, 5, "ai-01", "ai-05", "01"),
                match_seed(3, 1, 4, "ai-01", "ai-05", "01"),
                match_seed(3, 0, 4, "ai-01", "ai-05", "02")}) == 4


@pytest.mark.parametrize("seed", [77, 421])
def test_20_real_ai_bouts_commit_with_player_result_and_original_state_unchanged(seed):
    roster, league, pairs = start_day(seed)
    before_roster, before = deepcopy(roster), deepcopy(league)
    player_winner = pairs[0][1]
    updated, audit = commit_real_ai_matchday(roster, league, player_winner)
    assert roster == before_roster
    assert league == before
    assert len(audit) == 20
    assert all(item["winner"] in {item["a"], item["b"]} for item in audit)
    assert all(isinstance(item["turns"], int) and item["turns"] >= 0 for item in audit)
    assert all(item["method"] for item in audit)
    assert all(28 <= item["deck_size_a"] <= 40 and
               28 <= item["deck_size_b"] <= 40 for item in audit)
    assert all(item["deck_size_a"] == item["deck_size_b"] == 28 for item in audit)
    assert updated["day"] == 1
    assert len(updated["results"]) == 1
    assert len(updated["results"][0]) == 21
    assert len(updated["ai_bout_audit"]) == 1
    assert updated["ai_bout_audit"][0] == audit
    assert updated["results"][0][0]["winner"] == player_winner
    assert all(row["wins"]+row["losses"] == 1 for row in updated["wrestlers"])
    assert sum(row["wins"] for row in updated["wrestlers"]) == 21
    assert banzuke(updated)[-1]["rank"] == 42


def test_same_saved_pending_day_yields_identical_outcomes_without_reroll():
    roster, league, pairs = start_day(118)
    original = json.loads(json.dumps(league))
    a, audited_a = commit_real_ai_matchday(roster, league, PLAYER)
    b, audited_b = commit_real_ai_matchday(roster, original, PLAYER)
    assert a == b and audited_a == audited_b
    restored = json.loads(json.dumps(a))
    assert restored == a
    with pytest.raises(ValueError):
        commit_real_ai_matchday(roster, restored, PLAYER)


def test_invalid_player_or_missing_pending_pair_is_rejected():
    roster = make_roster(11, "Player")
    league = new_basho(roster)
    with pytest.raises(ValueError):
        commit_real_ai_matchday(roster, league, PLAYER)
    pairs = next_day_matches(league)
    with pytest.raises(ValueError):
        commit_real_ai_matchday(roster, league, "ai-60")
    with pytest.raises(ValueError):
        commit_real_ai_matchday(roster, league, PLAYER, max_turns=0)
    assert len(pairs) == 21 and league["day"] == 0


def test_simulation_failure_aborts_without_partial_results(monkeypatch):
    import kimarite.b12_ai_day as live
    roster, league, _ = start_day(88)
    baseline = deepcopy(league)
    original = live.simulate_ai_bout
    calls = {"n": 0}
    def fail_later(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 5:
            raise RuntimeError("forced incomplete AI test bout")
        return original(*args, **kwargs)
    monkeypatch.setattr(live, "simulate_ai_bout", fail_later)
    with pytest.raises(RuntimeError, match="forced incomplete"):
        live.commit_real_ai_matchday(roster, league, PLAYER)
    assert calls["n"] == 5
    assert league == baseline
    assert league["day"] == 0
    assert len(league["results"]) == 0


def test_15_day_real_ai_campaign_300_actual_bouts_no_repeats_or_hidden_results():
    # Only the player's match winner is a test fixture. Every other winner
    # comes from Tachiai and the current V5 AI playing the actual cards.
    roster = make_roster(126, "Player")
    league = new_basho(roster)
    all_pairs = set()
    for day in range(15):
        matches = next_day_matches(league)
        assert league["day"] == day
        assert len(league["results"]) == day
        assert all(row["wins"] + row["losses"] == day for row in league["wrestlers"])
        for a, b in matches:
            key = frozenset((a, b))
            assert key not in all_pairs
            all_pairs.add(key)
        # 8 wins, 7 losses for the created player in this test-only campaign.
        player_winner = PLAYER if day < 8 else matches[0][1]
        league, audits = commit_real_ai_matchday(roster, league, player_winner)
        assert len(audits) == 20
        assert all(row["wins"] + row["losses"] == day+1 for row in league["wrestlers"])
        assert len(league["ai_bout_audit"]) == day+1
        assert len(league["results"]) == day+1
        if day >= 1:
            # At least one of the AI wrestlers earned its first duplicate,
            # as its winning record grew over previous days.
            assert any(item["deck_size_a"] > 28 or item["deck_size_b"] > 28 for item in audits)
    assert len(all_pairs) == 315
    assert sum(len(day_results) for day_results in league["results"]) == 315
    assert sum(len(day_audit) for day_audit in league["ai_bout_audit"]) == 300
    assert all(row["wins"] + row["losses"] == 15 for row in banzuke(league))
    assert sum(row["wins"] for row in banzuke(league)) == 315
    assert len({row["name"] for row in banzuke(league)}) == 42
