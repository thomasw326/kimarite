"""R19 is a simulator-only ablation; approved card play is unchanged."""
from kimarite.catalog import card_by_name
from kimarite.effects import EffectContext
from kimarite.kimarite_effects import resolve_kimarite_play_effect
from kimarite.models import BoutState, FighterState, Side, Wrestler
from kimarite.kimarite_audit_v5 import audit


def test_kimarite_exchange_disabled_only_in_opt_in_mode():
    starter = card_by_name("Oshidashi")
    wrestler = Wrestler("Test", 3, 2, 1, starter, starter, starter)
    state = BoutState(FighterState(wrestler), FighterState(wrestler))
    state.position = 1
    state.disable_kimarite_exchange_effects = True
    resolve_kimarite_play_effect(state, Side.A, starter, EffectContext())
    assert state.momentum == 0
    state.disable_kimarite_exchange_effects = False
    resolve_kimarite_play_effect(state, Side.A, starter, EffectContext())
    assert state.momentum == 1


def test_r19_audit_flag_reported():
    data = audit(repetitions=1, max_turns=30, disable_kimarite_exchange_effects=True)
    assert data["disable_kimarite_exchange_effects"] is True
    assert data["planned_bouts"] == 210
    assert data["completed"] + sum(data["incomplete"].values()) == 210
