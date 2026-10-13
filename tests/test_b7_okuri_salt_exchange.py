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


@pytest.mark.parametrize("name", ["Okuridashi", "Okuritaoshi"])
@pytest.mark.parametrize("mode", ["position_to_momentum", "momentum_to_position"])
def test_okuri_exchange_discards_after_effect(name, mode):
    state = make_bout()
    state.fighter_a.hand = [card_by_name("Oshi"), card_by_name("Tsuki")]
    before = len(state.fighter_a.discard_pile)
    resolve_kimarite_play_effect(
        state, Side.A, card_by_name(name),
        EffectContext(choices={"mode": mode, "hand_index": 1}),
    )
    assert [c.name for c in state.fighter_a.hand] == ["Oshi"]
    assert len(state.fighter_a.discard_pile) == before + 1
    assert state.fighter_a.discard_pile[-1].name == "Tsuki"


@pytest.mark.parametrize("variant", ["R21-OKD-RS", "R21-OKT-RS"])
def test_b7_okuri_empty_hand_discards_just_searched_reversal(variant):
    from kimarite.r21_variant_rules import build_variant_card
    from kimarite.playing import play_card
    okuri = build_variant_card(variant, card_id=80001)
    reversal = card_by_name("Pull")
    other = card_by_name("Tsuki")
    state = make_bout()
    state.r20_active = True
    state.fighter_a.hand = [okuri]
    state.fighter_a.draw_pile = [other, reversal, card_by_name("Oshi")]
    play_card(state, Side.A, okuri)
    assert not state.fighter_a.hand
    assert state.fighter_a.discard_pile[-1].name == "Pull"
    assert [c.name for c in state.fighter_a.draw_pile] == ["Tsuki", "Oshi"]


@pytest.mark.parametrize("variant", ["R21-OKD-RS", "R21-OKT-RS"])
def test_b7_okuri_search_then_choose_discard(variant):
    from kimarite.r21_variant_rules import build_variant_card
    from kimarite.playing import play_card
    okuri = build_variant_card(variant, card_id=80002)
    state = make_bout()
    state.r20_active = True
    state.fighter_a.hand = [okuri, card_by_name("Oshi")]
    state.fighter_a.draw_pile = [card_by_name("Henka"), card_by_name("Tsuki")]
    play_card(state, Side.A, okuri, context=EffectContext(choices={"hand_index": 0}))
    assert [c.name for c in state.fighter_a.hand] == ["Henka"]
    assert state.fighter_a.discard_pile[-1].name == "Oshi"
