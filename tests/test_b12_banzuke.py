"""B12 basho boundary tests: exact created-player rank, stable elites, easy AI."""
from copy import deepcopy
import json

import pytest

from kimarite.b12_banzuke import end_of_basho, project_rank
from kimarite.b12_division_roster import load_formats, make_roster, validate_world
from kimarite.b12_league import PLAYER, commit_day, new_basho, next_day_matches


def complete_basho(roster, player_wins=8, *, seed=0):
    """Test-only outcomes for a proper 15-day, 315-match complete ledger."""
    league = new_basho(roster)
    for day in range(15):
        pairs = next_day_matches(league)
        winners = []
        for i, (a, b) in enumerate(pairs):
            if a == PLAYER:
                winner = PLAYER if day < player_wins else b
            elif b == PLAYER:
                winner = PLAYER if day < player_wins else a
            else:
                # Superior incoming rank wins: a clear source of qualifying
                # bottom-ranked AI for the overflow/relegation tests.
                rank = {w["id"]: w["rank"] for w in league["wrestlers"]}
                winner = a if rank[a] < rank[b] else b
            winners.append({"a": a, "b": b, "winner": winner})
        league = commit_day(league, winners)
    return league


@pytest.mark.parametrize("wins,expected", [(0, 42), (7, 42), (8, 40),
                                          (9, 36), (10, 32), (12, 24),
                                          (15, 12)])
def test_player_exact_two_ranks_per_net_win_from_42(wins, expected):
    roster = make_roster(710, "Player")
    league = complete_basho(roster, player_wins=wins)
    updated, report = end_of_basho(roster, league)
    assert report["player_from"] == 42
    assert report["player_to"] == expected
    assert updated["player"]["rank"] == expected
    assert len([w for w in updated["wrestlers"] if w["division"] == "top"]) == 41
    assert {w["format_id"] for w in updated["wrestlers"]} == {
        f["id"] for f in load_formats()
    }
    validate_world(updated)


def move_player_to(roster, rank):
    """Set up an otherwise valid ranked world for exact top-five slot cases."""
    copy = deepcopy(roster)
    for w in copy["wrestlers"]:
        if w["division"] == "top" and w["rank"] >= rank:
            w["rank"] += 1
    copy["player"]["rank"] = rank
    validate_world(copy)
    return copy


@pytest.mark.parametrize("initial_rank,win_count,target", [
    (7, 11, 1), (8, 9, 2), (9, 9, 3), (10, 9, 4), (7, 8, 5),
])
def test_elite_five_are_protected_and_shift_down_for_exact_player_slot(initial_rank, win_count, target):
    base = make_roster(88, "Player")
    initial = move_player_to(base, initial_rank)
    league = complete_basho(initial, player_wins=win_count)
    projected = max(1, min(42, project_rank(initial_rank, win_count, 15-win_count)))
    updated, report = end_of_basho(initial, league)
    assert updated["player"]["rank"] == projected == target
    elites = [w["wrestler_id"] for w in sorted(
        (x for x in initial["wrestlers"] if x["division"] == "top"), key=lambda x: x["rank"]
    )[:5]]
    assert report["protected_elites"] == elites
    elites_now = [next(w["rank"] for w in updated["wrestlers"] if w["wrestler_id"] == wid)
                  for wid in elites]
    assert elites_now == sorted(elites_now)
    expected_elite_slots = [n for n in range(1, 7) if n != projected][:5]
    assert elites_now == expected_elite_slots
    assert len({w["rank"] for w in updated["wrestlers"] if w["division"] == "top"} |
               {updated["player"]["rank"]}) == 42


def test_top_five_have_same_membership_order_if_player_is_not_in_top_five():
    roster = make_roster(400, "Player")
    frozen = [w["wrestler_id"] for w in roster["wrestlers"][:5]]
    updated, report = end_of_basho(roster, complete_basho(roster))
    assert updated["player"]["rank"] > 5
    assert report["protected_elites"] == frozen
    assert [w["wrestler_id"] for w in sorted(
        (w for w in updated["wrestlers"] if w["division"] == "top" and w["rank"] <= 5),
        key=lambda x: x["rank"]
    )] == frozen


def test_one_way_reserve_replacements_and_save_reload_without_duplication():
    roster = make_roster(51, "Player")
    original_queue = roster["reserve_queue"].copy()
    original_elites = [w["wrestler_id"] for w in roster["wrestlers"][:5]]
    archived_seen = set()
    entered = []
    for boundary in range(5):
        league = complete_basho(roster, player_wins=8, seed=boundary)
        prior = deepcopy(roster)
        updated, report = end_of_basho(roster, league)
        assert roster == prior
        assert updated["completed_basho"] == boundary + 1
        assert report["protected_elites"] == original_elites
        assert len(report["relegated"]) <= 3
        assert len(report["relegated"]) == len(report["promoted"])
        assert not archived_seen.intersection(report["promoted"])
        assert not archived_seen.intersection(report["relegated"])
        archived_seen.update(report["relegated"])
        entered.extend(report["promoted"])
        assert entered == original_queue[:len(entered)]
        assert updated["reserve_queue"] == original_queue[len(entered):]
        assert updated["archived_wrestlers"] == list(archived_seen) or set(updated["archived_wrestlers"]) == archived_seen
        assert all(w["wrestler_id"] in archived_seen and w["rank"] is None
                   for w in updated["wrestlers"] if w["division"] == "archived")
        assert all(w["wrestler_id"] in entered
                   for w in updated["wrestlers"] if w["division"] == "top"
                   and w["wrestler_id"] in original_queue)
        assert {w["format_id"] for w in updated["wrestlers"]} == {f["id"] for f in load_formats()}
        assert len(set(w["name"] for w in updated["wrestlers"])) == 60
        restored = json.loads(json.dumps(updated))
        validate_world(restored)
        assert restored == updated
        # Start next tournament at the NEW banzuke with everyone's W–L reset.
        new = new_basho(restored)
        assert all(w["wins"] == w["losses"] == 0 for w in new["wrestlers"])
        assert sorted(w["rank"] for w in new["wrestlers"]) == list(range(1, 43))
        roster = updated
    assert len(entered) <= 15
    assert len(original_queue) - len(entered) >= 4
    assert len(set(entered)) == len(entered)
    with pytest.raises(ValueError):
        end_of_basho(roster, complete_basho(roster))


def test_rank_update_requires_complete_15_day_42_person_ledger():
    roster = make_roster(710, "Player")
    league = new_basho(roster)
    with pytest.raises(ValueError):
        end_of_basho(roster, league)
    league = complete_basho(roster)
    corrupted = deepcopy(league)
    corrupted["wrestlers"][0]["wins"] = 0
    corrupted["wrestlers"][0]["losses"] = 0
    with pytest.raises(ValueError):
        end_of_basho(roster, corrupted)


def test_world_validator_rejects_repeat_format_reuse_after_promotion():
    roster = make_roster(220, "Player")
    updated, _ = end_of_basho(roster, complete_basho(roster))
    corrupted = deepcopy(updated)
    corrupted["wrestlers"][1]["format_id"] = corrupted["wrestlers"][0]["format_id"]
    with pytest.raises(ValueError):
        validate_world(corrupted)
