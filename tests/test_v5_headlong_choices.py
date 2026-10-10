"""Optional Tachiai Headlong Charge sacrifice choices."""
import pytest
from kimarite.catalog import card_by_name
from kimarite.models import BoutState, FighterState, Side, Wrestler
from kimarite.tachiai import compare_tachiai
from kimarite.tachiai_effects import resolve_prepared_tachiai


def make_bout():
    charge = card_by_name("Headlong Charge")
    neutral = card_by_name("Oshi")
    a = Wrestler("A", 2, 2, 2, charge, charge, charge)
    b = Wrestler("B", 2, 2, 2, neutral, neutral, neutral)
    state = BoutState(FighterState(a), FighterState(b))
    state.fighter_a.kimarite_zone = [card_by_name("Yorikiri"), card_by_name("Oshidashi")]
    state.fighter_a.draw_pile = [neutral, neutral, neutral]
    return state, compare_tachiai(a, b)


def test_headlong_decline_preserves_both_kimarite():
    state, comparison = make_bout()
    resolve_prepared_tachiai(state, comparison, sacrifice_choices={Side.A: None})
    assert [c.name for c in state.fighter_a.kimarite_zone] == ["Yorikiri", "Oshidashi"]


def test_headlong_can_sacrifice_selected_kimarite():
    state, comparison = make_bout()
    resolve_prepared_tachiai(state, comparison, sacrifice_choices={Side.A: 1})
    assert [c.name for c in state.fighter_a.kimarite_zone] == ["Yorikiri"]
    assert any(c.name == "Oshidashi" for c in state.fighter_a.discard_pile)


def test_headlong_rejects_invalid_choice():
    state, comparison = make_bout()
    with pytest.raises(ValueError, match="Invalid Headlong"):
        resolve_prepared_tachiai(state, comparison, sacrifice_choices={Side.A: 9})
