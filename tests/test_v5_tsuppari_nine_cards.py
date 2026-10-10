"""Tsuppari Tachiai injects three copies of each Oshi-package card."""
from collections import Counter

from kimarite.catalog import card_by_name
from kimarite.models import BoutState, FighterState, Wrestler, Card
from kimarite.tachiai import compare_tachiai
from kimarite.tachiai_effects import resolve_prepared_tachiai


def test_prepared_tsuppari_adds_nine_cards():
    tsuppari = card_by_name("Tsuppari")
    blank = Card(95001, "Test Blank")
    a = Wrestler("A", 2, 2, 2, card_by_name("Oshidashi"), tsuppari, blank)
    b = Wrestler("B", 2, 2, 2, card_by_name("Oshidashi"), blank, blank)
    state = BoutState(
        FighterState(a, draw_pile=[blank]),
        FighterState(b, draw_pile=[blank]),
    )
    resolve_prepared_tachiai(state, compare_tachiai(a, b))
    generated = [c for c in state.fighter_a.draw_pile if 20001 <= c.card_id <= 20009]
    assert len(generated) == 9
    assert Counter(c.name for c in generated) == {"Oshi": 3, "Tsuki": 3, "Shove": 3}
    assert len({c.card_id for c in generated}) == 9
