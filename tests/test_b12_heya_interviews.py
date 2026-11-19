"""Regression checks for Heya rewards affecting real draft and bout setup."""
import pytest

from kimarite.b11_live_opening import build_resolved_b11_opening
from kimarite.b11_pending_session import PendingB11Session
from kimarite.b11_player_draft import deal_block, remove_from_deck
from kimarite.catalog import card_by_name
from kimarite.models import Side
from kimarite.turns import apply_start_of_turn_exhaustion


def opening(kind=None, *, stack=None, rematch=None, committed=(0, 1, 2)):
    pending = PendingB11Session.start(
        "Heavy Hitter", "The Technician", ["Oshi", "Tsuki", "Shove"], seed=99,
    )
    pending.confirm(list(committed))
    pending.interview = {"kind": kind, "card": stack}
    pending.rematch_top_card = card_by_name(rematch) if rematch else None
    return build_resolved_b11_opening(pending, seed=99)


@pytest.mark.parametrize("stat", ["power", "technique", "spirit"])
def test_stat_bonus_changes_only_the_player_opening(stat):
    baseline = opening().comparison
    boosted = opening(stat).comparison
    assert getattr(boosted.wrestler_a, stat) == getattr(baseline.wrestler_a, stat) + 1
    assert boosted.wrestler_b == baseline.wrestler_b


def test_stamina_uses_the_player_threshold_in_combat():
    state = opening("stamina", committed=()).state
    own = state.fighter(Side.A)
    own.left_grip = own.right_grip = type(own.left_grip).NONE
    own.power = 6
    own.discard_pile = [card_by_name("Oshi")] * 9
    apply_start_of_turn_exhaustion(state, Side.A)
    assert own.power == 6
    own.discard_pile.append(card_by_name("Oshi"))
    apply_start_of_turn_exhaustion(state, Side.A)
    assert own.power == 5
    assert state.fighter(Side.B).exhaustion_threshold == 7


def test_rematch_and_interview_keep_both_draw_slots_even_for_the_same_name():
    state = opening("stack", stack="Tsuki", rematch="Tsuki").state
    first, second = state.fighter(Side.A).draw_pile[:2]
    assert first.name == second.name == "Tsuki"
    assert first is not second


def test_double_dip_only_returns_an_opening_card_when_all_three_were_committed():
    assert len(opening("double_dip", committed=(0, 1)).state.fighter_a.hand) == 1
    hand = opening("double_dip").state.fighter_a.hand
    assert len(hand) == 1 and hand[0].name in {"Oshi", "Tsuki", "Shove"}


def test_deal_keeps_guarantees_and_excludes_physical_copies():
    ids = [f"original:{i}" for i in range(28)] + [f"duplicate:{i}" for i in range(3)]
    deck, remaining = remove_from_deck(["Oshi"] * len(ids), ids, ids[:3])
    assert len(deck) == 28
    result = deal_block(deck, 88, remaining, guaranteed=remaining[:3], previous=remaining[-9:])
    selected = {card["instance_id"] for card in result}
    assert len(selected) == 9
    assert set(remaining[:3]) <= selected
    assert not selected.intersection(ids[:3] + remaining[-9:])
    with pytest.raises(ValueError, match="exclusions"):
        remove_from_deck(deck, remaining, remaining[:1])
