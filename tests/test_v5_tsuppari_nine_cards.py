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


def test_exchange_tsuppari_draws_without_refunding_play_or_milling():
    from kimarite.models import Side
    from kimarite.playing import play_card
    for prior in (None, "Oshi", "Tsuki", "Tsuppari", "Shove"):
        tsuppari = card_by_name("Tsuppari")
        blank = Card(95001, "Test Blank")
        a = Wrestler("A", 2, 2, 2, card_by_name("Oshidashi"), blank, blank)
        b = Wrestler("B", 2, 2, 2, card_by_name("Oshidashi"), blank, blank)
        state = BoutState(FighterState(a, hand=[tsuppari], draw_pile=[blank, blank, blank]), FighterState(b))
        state.fighter_a.plays_remaining = 1
        if prior:
            state.fighter_a.played_this_turn.append(card_by_name(prior))
        play_card(state, Side.A, tsuppari)
        assert state.fighter_a.plays_remaining == 0
        assert state.fighter_a.hand == [blank]
        assert state.fighter_a.draw_pile == [blank, blank]
        assert state.fighter_a.discard_pile == [tsuppari]
        assert state.position == (1 if prior else 0)
