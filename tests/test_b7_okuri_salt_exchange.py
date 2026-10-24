"""B7 targeted Exchange balance regression tests."""
import pytest
from kimarite.catalog import card_by_name
from kimarite.effects import EffectContext, resolve_exchange_effect
from kimarite.kimarite_effects import resolve_kimarite_play_effect
from kimarite.models import Side, BoutState, Card, FighterState, Wrestler


def make_bout():
    blank = Card(9990, 'Blank')
    a = Wrestler('A', 0, 0, 0, blank, blank, blank)
    b = Wrestler('B', 0, 0, 0, blank, blank, blank)
    return BoutState(FighterState(a), FighterState(b))


def test_salt_throw_grants_one_exchange_play():
    state = make_bout()
    before = state.fighter_a.plays_remaining
    resolve_exchange_effect(state, Side.A, card_by_name("Salt Throw"), EffectContext())
    assert state.fighter_a.plays_remaining == before + 1



@pytest.mark.parametrize("variant", ["R21-OKD-RS", "R21-OKT-RS"])
def test_b7_okuri_restored_search_keeps_reversal_in_hand(variant):
    from kimarite.r21_variant_rules import build_variant_card
    from kimarite.playing import play_card
    okuri = build_variant_card(variant, card_id=80001)
    state = make_bout()
    state.r20_active = True
    state.fighter_a.hand = [okuri]
    state.fighter_a.draw_pile = [card_by_name("Tsuki"), card_by_name("Pull")]
    play_card(state, Side.A, okuri)
    assert [c.name for c in state.fighter_a.hand] == ["Pull"]
    assert not state.fighter_a.discard_pile


def test_b7_okuridashi_requires_position_two():
    from kimarite.r21_variant_rules import variant_predicate
    state = make_bout()
    state.fighter_a.successful_reversal_this_turn = True
    state.momentum = 1
    state.position = 1
    assert not variant_predicate(state, Side.A, "R21-OKD-RS")
    state.position = 2
    assert variant_predicate(state, Side.A, "R21-OKD-RS")
