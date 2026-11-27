import pytest
from kimarite.catalog import card_by_name
from kimarite.effects import EffectContext, resolve_exchange_effect
from kimarite.models import BoutState, FighterState, GripState, Side, Wrestler
from kimarite.rules import effective_total_grip, improve_grip
from kimarite.temporary import add_temporary, remove_temporary, resolve_start_of_turn_temporaries

def bout():
    c = card_by_name("Oshi")
    w = Wrestler("W", 3, 2, 1, c, c, c)
    return BoutState(FighterState(w, draw_pile=[c, c]), FighterState(w))

def play(s, name):
    resolve_exchange_effect(s, Side.A, card_by_name(name), EffectContext())

@pytest.mark.parametrize("grip,temporary", [(False,False),(True,False),(False,True),(True,True)])
def test_maesabaki_draws_once_unless_both_succeed(grip, temporary):
    s = bout()
    if grip:
        s.fighter_b.left_grip = GripState.DEEP
    if temporary:
        add_temporary(s, Side.B, card_by_name("Hold Position"), phase="exchange")
    play(s, "Maesabaki")
    assert s.fighter_b.left_grip == GripState.NONE
    assert not s.fighter_b.temporary_zone
    assert len(s.fighter_a.hand) == int(not (grip and temporary))
    assert card_by_name("Maesabaki").spirit == 2

@pytest.mark.parametrize("grip", [False,True])
def test_hazuoshi_only_destabilizes_if_grip_removed(grip):
    s = bout()
    if grip:
        s.fighter_b.left_grip = GripState.DEEP
    play(s, "Hazuoshi")
    assert s.position == 1
    assert s.fighter_b.unstable == grip
    assert s.fighter_b.left_grip == (GripState.GRIP if grip else GripState.NONE)

@pytest.mark.parametrize("disrupted", [False,True])
def test_kannuki_suppression_and_completion(disrupted):
    s = bout()
    s.fighter_b.left_grip = GripState.DEEP
    play(s, "Kannuki")
    assert effective_total_grip(s, Side.B) == 0
    improve_grip(s, Side.B, "right")
    assert s.fighter_b.right_grip == GripState.GRIP
    if disrupted:
        remove_temporary(s, Side.A, s.fighter_a.temporary_zone[0], disrupted=True)
    else:
        resolve_start_of_turn_temporaries(s, Side.A)
    assert s.fighter_b.total_grip == (3 if disrupted else 0)
    assert s.momentum == (0 if disrupted else 1)

def test_kannuki_momentum_against_gripless():
    s = bout()
    play(s, "Kannuki")
    resolve_start_of_turn_temporaries(s, Side.A)
    assert s.momentum == 1

def test_ottsuke_blocks_pending_deep_grip_but_not_existing_grip():
    s = bout()
    s.fighter_b.left_grip = GripState.DEEP
    add_temporary(s, Side.B, card_by_name("Attempt Deep Inside Grip"), phase="exchange")
    play(s, "Ottsuke")
    assert effective_total_grip(s, Side.B) == 1
    resolve_start_of_turn_temporaries(s, Side.B)
    assert s.fighter_b.right_grip == GripState.NONE
    assert s.momentum == 1
    c = card_by_name("Ottsuke")
    assert (c.power,c.technique,c.spirit) == (1,1,1)
