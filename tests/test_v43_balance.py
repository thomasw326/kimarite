"""V4.3 rules regression tests for the local simulation."""
from kimarite.catalog import card_by_name
from kimarite.effects import EffectContext, resolve_exchange_effect
from kimarite.kimarite import kimarite_is_satisfied
from kimarite.kimarite_effects import resolve_kimarite_play_effect
from kimarite.models import BoutState, Card, FighterState, GripState, Side, Wrestler
from kimarite.rules import gain_push
from kimarite.temporary import add_temporary, remove_temporary, resolve_start_of_turn_temporaries


def bout():
    blank = Card(999, "Blank")
    a = Wrestler("A", 0, 0, 0, blank, blank, blank)
    b = Wrestler("B", 0, 0, 0, blank, blank, blank)
    return BoutState(FighterState(a), FighterState(b))


def test_hikiotoshi_draw_no_grip():
    s = bout()
    s.fighter_a.draw_pile = [
        card_by_name("Oshi"),
        card_by_name("Tsuki"),
    ]

    resolve_kimarite_play_effect(
        s,
        Side.A,
        card_by_name("Hikiotoshi"),
        EffectContext(),
    )

    assert s.momentum == 0
    assert len(s.fighter_a.hand) == 1
    assert len(s.fighter_a.draw_pile) == 1
    assert {
        s.fighter_a.hand[0].name,
        s.fighter_a.draw_pile[0].name,
    } == {"Oshi", "Tsuki"}

def test_morozashi_survival_push_and_momentum():
    s = bout()
    add_temporary(s, Side.A, card_by_name("Morozashi"), phase="exchange")
    resolve_start_of_turn_temporaries(s, Side.A)
    assert s.position == 1
    assert s.momentum == 1


def test_oshi_push_play_draw():
    s = bout()
    s.momentum = 1
    s.fighter_a.draw_pile = [card_by_name("Tsuki")]
    resolve_exchange_effect(s, Side.A, card_by_name("Oshi"), EffectContext())
    assert [card.name for card in s.fighter_a.hand] == ["Tsuki"]
    assert s.fighter_a.discard_pile == []
    assert s.fighter_a.plays_remaining == 3
    assert s.position == 1


def test_tsuridashi_needs_nonnegative_position():
    s = bout()
    s.fighter_a.left_grip = GripState.DEEP
    s.fighter_a.right_grip = GripState.GRIP
    s.fighter_a.power = 6
    s.position = -1
    assert not kimarite_is_satisfied(s, Side.A, card_by_name("Tsuridashi"))
    s.position = 0
    assert kimarite_is_satisfied(s, Side.A, card_by_name("Tsuridashi"))


def test_sidestep_prevents_both_players_push():
    s = bout()
    s.side_by_side_owner = Side.A
    s.side_by_side_distance = 2
    add_temporary(s, Side.A, card_by_name("Sidestep"), phase="exchange")
    gain_push(s, Side.A, 3)
    gain_push(s, Side.B, 2)
    assert s.position == 0
    assert s.side_by_side_owner is Side.A
    assert len(s.fighter_a.temporary_zone) == 1
