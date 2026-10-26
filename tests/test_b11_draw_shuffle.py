"""B11 draw pile is seeded and shuffled, not left in roster JSON order."""
import json
import random
from kimarite.b10_human_session import ROSTER_PATH, roster
from kimarite.b11_live_opening import build_resolved_b11_opening
from kimarite.b11_pending_session import PendingB11Session
from kimarite.catalog import card_by_name


def test_remaining_draw_pile_matches_seeded_shuffle_without_commits():
    human, opponent = roster()[:2]
    names = json.loads(ROSTER_PATH.read_text())["decks"][human]["cards"]
    allocated = names[:3]
    pending = PendingB11Session.start(human, opponent, allocated, seed=23)
    pending.confirm([])
    actual = build_resolved_b11_opening(pending, seed=23).state.fighter_a.draw_pile
    original = [card_by_name(n) for n in names]
    remaining = pending.phase.decision.unallocated_deck(pending.phase.opening, original)
    random.Random(23 * 2).shuffle(remaining)
    assert [c.name for c in actual] == [c.name for c in remaining]
    assert [c.name for c in actual] != names[3:]
    again = build_resolved_b11_opening(pending, seed=23).state.fighter_a.draw_pile
    assert [c.name for c in again] == [c.name for c in actual]


def test_different_seeds_change_shuffled_draw_order():
    human, opponent = roster()[:2]
    names = json.loads(ROSTER_PATH.read_text())["decks"][human]["cards"]
    pending = PendingB11Session.start(human, opponent, names[:3])
    pending.confirm([])
    a = build_resolved_b11_opening(pending, seed=23).state.fighter_a.draw_pile
    b = build_resolved_b11_opening(pending, seed=24).state.fighter_a.draw_pile
    assert [c.name for c in a] != [c.name for c in b]
