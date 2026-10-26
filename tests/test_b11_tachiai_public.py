"""Pre-Tachiai HTTP payload cannot reveal any AI opening secrets."""
import json
import pytest

from kimarite.b11_player_opening import PlayerOpening
from kimarite.b11_tachiai_phase import PendingPlayerTachiai
from kimarite.b11_tachiai_public import pending_tachiai_snapshot
from kimarite.catalog import card_by_name


def test_pending_payload_excludes_hidden_ai_tachiai():
    opening = PlayerOpening.from_names(
        [card_by_name(n) for n in ("Oshi", "Tsuki", "Shove")],
        ("Oshi", "Tsuki", "Shove"),
    )
    phase = PendingPlayerTachiai(opening)
    result = pending_tachiai_snapshot(phase, "Pressure Fighter", "The Technician")
    assert result["phase"] == "choose_tachiai"
    assert [c["name"] for c in result["tachiai_choice"]["cards"]] == ["Oshi", "Tsuki", "Shove"]
    assert result["opening"] is None
    assert result["events"] == []
    assert result["legal_plays"] == []
    assert not result["can_end_turn"]
    raw = json.dumps(result).lower()
    for forbidden in (
        "starting_kimarite", "prepared_tachiai", "top_of_deck",
        "tachiai_orbs", "comparison", "advantage", "draw_pile",
        "uwatenage", "attempt deep outside grip",
    ):
        assert forbidden not in raw


def test_pending_snapshot_unavailable_after_confirm():
    deck = [card_by_name(n) for n in ("Oshi", "Tsuki", "Shove")]
    phase = PendingPlayerTachiai(PlayerOpening.from_names(deck, ("Oshi", "Tsuki", "Shove")))
    phase.choose([])
    with pytest.raises(ValueError, match="no longer pending"):
        pending_tachiai_snapshot(phase, "Player", "AI")
