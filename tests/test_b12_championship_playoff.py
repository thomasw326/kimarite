from copy import deepcopy
from types import SimpleNamespace

import pytest

from kimarite.b12_campaign_web import campaign_request
from kimarite.b12_division_roster import make_roster
from kimarite.b12_league import PLAYER, commit_day, new_basho, next_day_matches
from kimarite.models import Side


def finished_basho():
    roster = make_roster(902, "Player")
    league = new_basho(roster)
    for _ in range(15):
        league = commit_day(league, [
            {"a": a, "b": b, "winner": a}
            for a, b in next_day_matches(league)
        ])
    return roster, league


@pytest.mark.parametrize("size", [2, 3, 4, 5, 8])
def test_knockout_has_one_champion_and_keeps_regular_records(monkeypatch, size):
    roster, league = finished_basho()
    ranked = sorted(league["wrestlers"], key=lambda w: w["id"] == PLAYER)
    for i, row in enumerate(ranked):
        row.update(wins=12 if i < size else 8, losses=3 if i < size else 7)
    monkeypatch.setattr("kimarite.b12_campaign_web.simulate_ai_bout",
                        lambda a, b, *args, **kwargs: {
                            "a": a["id"], "b": b["id"], "winner": a["id"], "method": "Yorikiri",
                        })
    request = {"roster": roster, "league": league}
    first = campaign_request("/api/b12/campaign/playoff", request)["league"]
    assert first == campaign_request("/api/b12/campaign/playoff", request)["league"]
    assert first["champion_id"] in {row["id"] for row in ranked[:size]}
    assert len(first["playoff_matches"]) == size - 1
    assert first["day"] == 15
    assert first["wrestlers"] == league["wrestlers"]
    assert first["results"] == league["results"]
    assert campaign_request("/api/b12/campaign/playoff", {"roster": roster, "league": first})["league"] == first


def test_player_must_play_their_tiebreaker():
    roster, league = finished_basho()
    before = deepcopy(league)
    opponent = next(row for row in league["wrestlers"] if row["id"] != PLAYER)
    opponent.update(wins=15, losses=0)
    for row in league["wrestlers"]:
        if row is not opponent and row["id"] != PLAYER and row["wins"] == 15:
            row.update(wins=14, losses=1)
    next_bout = campaign_request("/api/b12/campaign/playoff", {"roster": roster, "league": league})
    assert next_bout["opponent"]["id"] == opponent["id"]
    assert next_bout["seed"] < 2**53
    request = {"roster": roster, "league": next_bout["league"]}
    with pytest.raises(ValueError, match="finished championship bout"):
        campaign_request("/api/b12/campaign/playoff/resolve", request)
    fighters = {Side.A: SimpleNamespace(wrestler=SimpleNamespace(name=roster["player"]["name"])),
                Side.B: SimpleNamespace(wrestler=SimpleNamespace(name=opponent["name"]))}
    state = SimpleNamespace(winner=Side.A, win_method="Oshidashi", fighter_a=fighters[Side.A],
                            fighter_b=fighters[Side.B])
    session = SimpleNamespace(b12_campaign=next_bout["bout"], finished=True, state=state)
    updated = campaign_request("/api/b12/campaign/playoff/resolve", request, session=session)["league"]
    assert updated["champion_id"] == PLAYER
    assert updated["playoff_matches"][0]["method"] == "Oshidashi"
    assert updated["results"] == before["results"]
