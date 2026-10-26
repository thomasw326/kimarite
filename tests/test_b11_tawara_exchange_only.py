"""Use the Tawara has an Exchange-only effect in player-controlled B11."""
import json
from collections import Counter

from kimarite.b10_card_info import card_info
from kimarite.b10_human_session import ROSTER_PATH, roster
from kimarite.b11_live_opening import build_resolved_b11_opening
from kimarite.b11_pending_session import PendingB11Session
from kimarite.catalog import card_by_name


def test_tawara_display_says_exchange_only():
    info = card_info(card_by_name("Use the Tawara"))
    assert info["timing"] == "Exchange"
    assert "search" in info["description"].lower()


def test_committed_tawara_does_not_search_kimarite_during_tachiai():
    records = json.loads(ROSTER_PATH.read_text())["decks"]
    human = next(name for name in roster() if "Use the Tawara" in records[name]["cards"])
    opponent = next(name for name in roster() if name != human)
    names = records[human]["cards"]
    chosen = ["Use the Tawara"] + [name for name in names if name != "Use the Tawara"][:2]
    pending = PendingB11Session.start(human, opponent, chosen, seed=321)
    pending.confirm([0])
    state = build_resolved_b11_opening(pending, seed=321).state
    own = state.fighter_a
    assert not any("searches" in event and "after Use the Tawara" in event for event in state.event_log)
    assert "Use the Tawara" in [c.name for c in own.draw_pile]
    assert Counter(c.name for c in own.kimarite_zone) == Counter()
