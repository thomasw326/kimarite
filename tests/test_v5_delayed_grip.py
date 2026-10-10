"""Sheet parity: Tsuri, Yori, Gaburi are surviving delayed Tempos."""
from kimarite.catalog import card_by_name
from kimarite.effects import EffectContext, resolve_exchange_effect
from kimarite.models import BoutState, FighterState, Wrestler, GripState, Side
from kimarite.temporary import resolve_start_of_turn_temporaries


def bout():
    kimarite = card_by_name("Oshidashi")
    wrestler_a = Wrestler("A", 2, 2, 2, kimarite, kimarite, kimarite)
    wrestler_b = Wrestler("B", 2, 2, 2, kimarite, kimarite, kimarite)
    return BoutState(FighterState(wrestler_a), FighterState(wrestler_b))


def test_tsuri_delayed_three_push_when_strong_and_gripping():
    s = bout()
    s.fighter_a.power = 5
    s.fighter_a.left_grip = GripState.DEEP
    resolve_exchange_effect(s, Side.A, card_by_name("Tsuri"), EffectContext())
    assert s.fighter_a.power == 6
    assert s.position == 0
    resolve_start_of_turn_temporaries(s, Side.A)
    assert s.position == 3


def test_yori_delayed_momentum_depends_on_grip_comparison():
    s = bout()
    s.fighter_a.left_grip = GripState.GRIP
    resolve_exchange_effect(s, Side.A, card_by_name("Yori"), EffectContext())
    assert s.position == 1
    resolve_start_of_turn_temporaries(s, Side.A)
    assert s.momentum == 3


def test_gaburi_creates_kimarite_only_if_power_exceeds_opponent():
    s = bout()
    s.fighter_a.power = 5
    s.fighter_b.power = 4
    s.fighter_a.left_grip = GripState.GRIP
    resolve_exchange_effect(s, Side.A, card_by_name("Gaburi"), EffectContext())
    assert s.momentum == 1
    assert not s.fighter_a.kimarite_zone
    resolve_start_of_turn_temporaries(s, Side.A)
    assert [c.name for c in s.fighter_a.kimarite_zone] == ["Yorikiri"]
