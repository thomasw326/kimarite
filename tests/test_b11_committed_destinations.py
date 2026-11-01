"""Player Tachiai card destinations follow Classic opening rules, not Exchange discard."""
import json
import pytest

from kimarite.b10_human_session import ROSTER_PATH, roster
from kimarite.b11_live_opening import build_resolved_b11_opening
from kimarite.b11_pending_session import PendingB11Session


def opening(cards, indices):
    human, opponent = roster()[:2]
    pending = PendingB11Session.start(human, opponent, cards, seed=23)
    pending.confirm(indices)
    return build_resolved_b11_opening(pending).state.fighter_a


def test_committed_kimarite_starts_in_zone_not_discard():
    human = roster()[0]
    deck = json.loads(ROSTER_PATH.read_text())["decks"][human]["cards"]
    from kimarite.catalog import card_by_name
    kimarite = next(n for n in deck if card_by_name(n).is_kimarite)
    ordinary = [n for n in deck if not card_by_name(n).is_kimarite]
    own = opening([kimarite, ordinary[0], ordinary[1]], [0])
    assert [c.name for c in own.kimarite_zone] == [kimarite]
    assert all(c.name != kimarite for c in own.discard_pile)
    assert len(own.hand) == 2


def test_committed_ordinary_recycles_to_bottom_of_draw_pile():
    human = roster()[0]
    deck = json.loads(ROSTER_PATH.read_text())["decks"][human]["cards"]
    from kimarite.catalog import card_by_name
    ordinary = [n for n in deck if not card_by_name(n).is_kimarite and n not in
                {"Shiko Stomp", "Salt Throw", "Nekodamashi", "Headlong Charge", "Oshi", "Tsuki"}]
    assert len(ordinary) >= 3
    own = opening(ordinary[:3], [0])
    assert own.draw_pile[-1].name == ordinary[0]
    assert own.discard_pile == []
    assert len(own.hand) == 2


def test_uncommitted_kimarite_stays_in_hand():
    human = roster()[0]
    deck = json.loads(ROSTER_PATH.read_text())["decks"][human]["cards"]
    from kimarite.catalog import card_by_name
    kimarite = next(n for n in deck if card_by_name(n).is_kimarite)
    ordinary = [n for n in deck if not card_by_name(n).is_kimarite]
    own = opening([kimarite, ordinary[0], ordinary[1]], [])
    assert any(c.name == kimarite for c in own.hand)
    assert not own.kimarite_zone
