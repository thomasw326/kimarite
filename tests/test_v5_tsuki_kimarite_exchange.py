"""Exchange effects of the two four-card Tsuki Kimarite."""
from kimarite.catalog import card_by_name
from kimarite.effects import EffectContext
from kimarite.kimarite_effects import resolve_kimarite_play_effect
from kimarite.models import BoutState, Card, FighterState, Side, Wrestler


def _bout(position=0, momentum=0):
    tsukidashi = card_by_name("Tsukidashi")
    blank = Card(98011, "Test Blank")
    w = Wrestler("A", 2, 2, 2, tsukidashi, blank, blank)
    return BoutState(
        FighterState(w, draw_pile=[blank, blank], plays_remaining=1),
        FighterState(w, draw_pile=[blank]),
        position=position, momentum=momentum,
    )


def test_tsukidashi_position_advantage_draws_and_grants_play_not_momentum():
    state = _bout(position=1, momentum=0)
    resolve_kimarite_play_effect(state, Side.A, card_by_name("Tsukidashi"), EffectContext())
    assert len(state.fighter_a.hand) == 1
    assert state.momentum == 0
    assert state.fighter_a.plays_remaining == 2


def test_tsukidashi_without_position_has_no_bonus():
    state = _bout()
    resolve_kimarite_play_effect(state, Side.A, card_by_name("Tsukidashi"), EffectContext())
    assert not state.fighter_a.hand
    assert state.momentum == 0


def test_tsukitaoshi_exchange_bonus_does_not_require_momentum():
    state = _bout(momentum=-1)
    resolve_kimarite_play_effect(state, Side.A, card_by_name("Tsukitaoshi"), EffectContext())
    assert state.fighter_a.plays_remaining == 2
    assert len(state.fighter_a.draw_pile) == 1
    assert len(state.fighter_a.hand) == 0
    assert len(state.fighter_a.discard_pile) == 1
