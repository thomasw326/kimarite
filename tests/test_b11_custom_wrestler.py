"""The player may create a wrestler without choosing a B9/B10 preset identity."""
import pytest

from kimarite.b11_player_draft import STARTERS, options_for, validate_draft
from kimarite.b11_pending_session import PendingB11Session
from kimarite.b11_live_opening import build_resolved_b11_opening, start_b11_human_bout
from kimarite.b10_human_session import roster
from kimarite.models import Stat


def drafted_deck(seed=723):
    starting = list(STARTERS)
    picks = []
    while len(starting) + len(picks) < 28:
        picks.append(options_for(starting, picks, seed)[0])
    return validate_draft(starting, picks, seed)


@pytest.mark.parametrize("stats,primary", [
    ({"power": 2, "technique": 1, "spirit": 0}, Stat.POWER),
    ({"power": 0, "technique": 2, "spirit": 1}, Stat.TECHNIQUE),
    ({"power": 1, "technique": 0, "spirit": 2}, Stat.SPIRIT),
])
def test_custom_player_name_and_stats_survive_live_bout(stats, primary):
    name = "My Rikishi"
    assert name not in roster()
    deck = drafted_deck()
    pending = PendingB11Session.start(
        name, "The Technician", deck[:3], drafted_deck=deck,
        created_stats=stats, seed=723,
    )
    snapshot = pending.snapshot()
    assert snapshot["phase"] == "choose_tachiai"
    assert snapshot["human"]["name"] == name
    assert snapshot["opponent"]["name"] == "The Technician"
    assert snapshot["opening"] is None

    pending.confirm([0, 2])
    result = build_resolved_b11_opening(pending, seed=723)
    own = result.state.fighter_a.wrestler
    other = result.state.fighter_b.wrestler
    assert own.name == name
    assert own.primary == primary
    assert (own.base_power, own.base_technique, own.base_spirit) == (
        stats["power"], stats["technique"], stats["spirit"]
    )
    assert sum((other.base_power, other.base_technique, other.base_spirit)) == 6
    assert other.name == "The Technician"
    assert len(result.state.fighter_a.draw_pile) <= len(deck)


def test_custom_player_can_enter_interactive_human_bout():
    deck = drafted_deck(517)
    pending = PendingB11Session.start(
        "Drafted Rikishi", "Heavy Hitter", deck[:3], drafted_deck=deck,
        created_stats={"power": 0, "technique": 1, "spirit": 2},
        seed=517,
    )
    pending.confirm([0])
    bout = start_b11_human_bout(pending)
    assert bout.state.fighter_a.wrestler.name == "Drafted Rikishi"
    assert bout.state.fighter_b.wrestler.name == "Heavy Hitter"


@pytest.mark.parametrize("name", ["", " ", "  Wrestler", "Wrestler  ", "X"*33, "a\nBad"])
def test_invalid_custom_wrestler_names_rejected(name):
    deck = drafted_deck()
    with pytest.raises(ValueError, match="name"):
        PendingB11Session.start(
            name, "The Technician", deck[:3], drafted_deck=deck,
            created_stats={"power": 2, "technique": 1, "spirit": 0},
        )


def test_custom_player_requires_both_real_draft_and_chosen_stats():
    deck = drafted_deck()
    with pytest.raises(ValueError, match="drafted deck and chosen stats"):
        PendingB11Session.start(
            "My Rikishi", "The Technician", deck[:3],
            created_stats={"power": 2, "technique": 1, "spirit": 0},
        )
    with pytest.raises(ValueError, match="drafted deck and chosen stats"):
        PendingB11Session.start(
            "My Rikishi", "The Technician", deck[:3], drafted_deck=deck,
        )


def test_custom_player_still_requires_approved_ai_opponent():
    deck = drafted_deck()
    with pytest.raises(ValueError, match="Opponent"):
        PendingB11Session.start(
            "My Rikishi", "Not an AI", deck[:3], drafted_deck=deck,
            created_stats={"power": 2, "technique": 1, "spirit": 0},
        )
