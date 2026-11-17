"""One-to-one seeded B12 60-format world roster, before standings integration."""
from collections import Counter
import copy
import json

import pytest

from kimarite.b12_division_roster import (
    ACTIVE_AI, AI_COUNT, BASHO_COUNT, PLAYER_RANK, RESERVE_AI,
    load_formats, load_shikona, make_roster, validate_roster,
)


def test_source_has_60_distinct_formats_and_existing_fictional_names():
    formats = load_formats()
    assert len(formats) == AI_COUNT == 60
    assert {x["id"] for x in formats} == {f"{i:02d}" for i in range(1, 61)}
    assert Counter(f["style_proxy"] for f in formats) == Counter({
        s: 4 for s in {f["style_proxy"] for f in formats}
    })
    assert len({f["style_proxy"] for f in formats}) == 15
    assert len(load_shikona()) == 69
    assert len(set(load_shikona())) == 69


@pytest.mark.parametrize("seed", [0, 1, 2, 17, 23, 20261117, 2**45])
def test_one_to_one_60_format_assignment_at_campaign_creation(seed):
    roster = make_roster(seed, "My Created Rikishi")
    validate_roster(roster)
    wrestlers = roster["wrestlers"]
    assert len(wrestlers) == 60
    assert len(set(w["format_id"] for w in wrestlers)) == 60
    assert {w["format_id"] for w in wrestlers} == {f["id"] for f in load_formats()}
    assert len(set(w["name"] for w in wrestlers)) == 60
    assert len(set(w["wrestler_id"] for w in wrestlers)) == 60
    assert Counter(w["ai_style"] for w in wrestlers) == Counter({
        s: 4 for s in {f["style_proxy"] for f in load_formats()}
    })
    assert [w["rank"] for w in wrestlers[:ACTIVE_AI]] == list(range(1, 42))
    assert all(w["division"] == "top" for w in wrestlers[:ACTIVE_AI])
    assert all(w["rank"] is None and w["division"] == "reserve"
               for w in wrestlers[ACTIVE_AI:])
    assert roster["player"] == {"name": "My Created Rikishi", "rank": PLAYER_RANK}
    assert len(roster["reserve_queue"]) == RESERVE_AI == 19
    assert roster["reserve_queue"] == [w["wrestler_id"] for w in wrestlers[41:]]
    assert BASHO_COUNT - 1 == 5
    assert RESERVE_AI >= 3 * (BASHO_COUNT - 1)


def test_same_seed_and_save_restore_preserve_name_style_format_and_rank():
    a = make_roster(190, "My Rikishi")
    b = make_roster(190, "My Rikishi")
    assert a == b
    restored = json.loads(json.dumps(a, ensure_ascii=False))
    validate_roster(restored)
    assert restored == a


def test_new_run_randomizes_both_active_formats_and_display_names():
    a, b = make_roster(111, "My Rikishi"), make_roster(222, "My Rikishi")
    assert [w["format_id"] for w in a["wrestlers"]] != [
        w["format_id"] for w in b["wrestlers"]
    ]
    assert [w["name"] for w in a["wrestlers"]] != [
        w["name"] for w in b["wrestlers"]
    ]
    assert {w["format_id"] for w in a["wrestlers"][:41]} != {
        w["format_id"] for w in b["wrestlers"][:41]
    }


def test_existing_player_name_is_excluded_from_ai_display_names():
    a = make_roster(113, "gOzAn")
    assert "gozan" not in {w["name"].casefold() for w in a["wrestlers"]}
    assert len({w["name"].casefold() for w in a["wrestlers"]}) == 60


@pytest.mark.parametrize("bad", [None, "", "  "])
def test_missing_player_name_rejected(bad):
    with pytest.raises(ValueError):
        make_roster(100, bad)


@pytest.mark.parametrize("bad", [None, "23", 2.5, True])
def test_invalid_seed_rejected(bad):
    with pytest.raises(TypeError):
        make_roster(bad, "My Rikishi")


@pytest.mark.parametrize("field", ["format_id", "wrestler_id", "name", "ai_style"])
def test_duplicates_and_wrong_style_are_rejected(field):
    roster = make_roster(12345, "My Rikishi")
    corrupted = copy.deepcopy(roster)
    corrupted["wrestlers"][1][field] = corrupted["wrestlers"][0][field]
    with pytest.raises(ValueError):
        validate_roster(corrupted)


def test_corrupt_reserve_queue_and_player_rank_are_rejected():
    roster = make_roster(12345, "My Rikishi")
    altered = copy.deepcopy(roster)
    altered["reserve_queue"] = altered["reserve_queue"][:-1]
    with pytest.raises(ValueError):
        validate_roster(altered)
    altered = copy.deepcopy(roster)
    altered["player"]["rank"] = 41
    with pytest.raises(ValueError):
        validate_roster(altered)


def test_original_frameworks_not_mutated_by_a_seeded_roster():
    original = load_formats()
    make_roster(100, "My Rikishi")
    assert load_formats() == original
