from kimarite.catalog import card_by_name
from kimarite.effects import EffectContext, resolve_exchange_effect
from kimarite.models import BoutState, FighterState, Side, Wrestler
from kimarite.rules import lose_power, make_unstable
from kimarite.temporary import remove_temporary, resolve_start_of_turn_temporaries
from kimarite.turns import apply_start_of_turn_exhaustion

def make_bout():
    c = card_by_name("Oshi")
    w = Wrestler("W", 3, 2, 1, c, c, c)
    return BoutState(FighterState(w, power=5, draw_pile=[c], discard_pile=[c]*7), FighterState(w))

def test_ankogata_permanent_protection_and_disruption():
    s = make_bout()
    resolve_exchange_effect(s, Side.A, card_by_name("Ankogata"), EffectContext())
    assert s.fighter_a.power == 6
    resolve_start_of_turn_temporaries(s, Side.A)
    assert len(s.fighter_a.temporary_zone) == 1
    lose_power(s, Side.A, 2)
    make_unstable(s, Side.A)
    apply_start_of_turn_exhaustion(s, Side.A)
    assert s.fighter_a.power == 6
    assert not s.fighter_a.unstable
    remove_temporary(s, Side.A, s.fighter_a.temporary_zone[0], disrupted=True)
    lose_power(s, Side.A, 2)
    make_unstable(s, Side.A)
    assert s.fighter_a.power == 4
    assert s.fighter_a.unstable

def test_ankogata_does_not_clear_existing_unstable():
    s = make_bout()
    make_unstable(s, Side.A)
    resolve_exchange_effect(s, Side.A, card_by_name("Ankogata"), EffectContext())
    assert s.fighter_a.unstable

def test_ankogata_does_not_prevent_empty_deck_defeat():
    s = make_bout()
    resolve_exchange_effect(s, Side.A, card_by_name("Ankogata"), EffectContext())
    s.fighter_a.draw_pile.clear()
    apply_start_of_turn_exhaustion(s, Side.A)
    assert s.winner == Side.B
