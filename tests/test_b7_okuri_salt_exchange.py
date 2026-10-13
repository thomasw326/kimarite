"""B7 targeted Exchange balance regression tests."""
import pytest
from kimarite.catalog import card_by_name
from kimarite.effects import EffectContext, resolve_exchange_effect
from kimarite.kimarite_effects import resolve_kimarite_play_effect
from kimarite.models import Side
from tests.helpers import make_bout


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
