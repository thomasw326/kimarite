"""New Power cards: threshold payoffs and fallback draws."""
from kimarite.catalog import card_by_name
from kimarite.effects import EffectContext, IllegalPlay, resolve_exchange_effect
from kimarite.models import BoutState, Card, FighterState, Side, Wrestler


def state(power=7, enemy_power=4):
    blank = Card(51000, "Blank")
    w = Wrestler("A", 4, 1, 1, blank, blank, blank)
    x = Wrestler("B", 4, 1, 1, blank, blank, blank)
    return BoutState(FighterState(w, power=power, draw_pile=[blank]), FighterState(x, power=enemy_power))


def test_driving_force_power_payoff_and_draw_fallback():
    s = state()
    resolve_exchange_effect(s, Side.A, card_by_name("Driving Force — Power Payoff"),
                            EffectContext(choices={"mode":"power_payoff"}))
    assert (s.position, s.momentum) == (1, 1)
    weaker = state(power=6)
    resolve_exchange_effect(weaker, Side.A, card_by_name("Driving Force — Power Payoff"),
                            EffectContext(choices={"mode":"draw"}))
    assert len(weaker.fighter_a.hand) == 1
    assert (weaker.position, weaker.momentum) == (0, 0)


def test_crushing_pressure_crush_and_draw_fallback():
    s = state(power=7, enemy_power=4)
    resolve_exchange_effect(s, Side.A, card_by_name("Crushing Pressure — Power Crusher"),
                            EffectContext(choices={"mode":"power_crusher"}))
    assert s.momentum == 1
    assert s.fighter_b.power == 3
    weaker = state(power=7, enemy_power=5)
    resolve_exchange_effect(weaker, Side.A, card_by_name("Crushing Pressure — Power Crusher"),
                            EffectContext(choices={"mode":"draw"}))
    assert len(weaker.fighter_a.hand) == 1
    assert weaker.fighter_b.power == 5
