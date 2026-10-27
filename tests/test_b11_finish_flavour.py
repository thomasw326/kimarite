"""B11 descriptive finishing labels; combat outcome stays unchanged."""
import pytest
from kimarite.catalog import card_by_name
from kimarite.models import BoutState, Card, FighterState, Side, Wrestler, GripState


def setup(p=2,t=1,s=0):
    c=card_by_name("Oshi")
    a=FighterState(Wrestler("Winner",p,t,s,c,c,c))
    b=FighterState(Wrestler("Loser",0,0,0,c,c,c))
    state=BoutState(a,b)
    state.b11_explain_wins=True
    return state


@pytest.mark.parametrize("stats,expected",[
    ((2,1,0),"Tsukiotoshi"),
    ((1,2,0),"Hikiotoshi"),
    ((0,1,2),"Hatakikomi"),
])
def test_power_defeat_uses_winners_strongest_stat(stats,expected):
    state=setup(*stats)
    state.declare_winner(Side.A,"Power")
    assert state.winner is Side.A
    assert state.win_method==expected
    assert state.win_source=="power_loss"
    assert state.b11_victory_details["source"]=="power_loss"


@pytest.mark.parametrize("grip,expected",[(GripState.NONE,"Oshidashi"),(GripState.GRIP,"Yorikiri")])
def test_ringout_preserves_grip_based_method(grip,expected):
    state=setup()
    state.fighter_a.left_grip=grip
    state.win_source="ringout"
    state.declare_winner(Side.A,expected)
    assert state.win_method==expected


def test_shove_forceout_is_oshidashi_even_with_grip():
    state=setup()
    state.fighter_a.left_grip=GripState.GRIP
    state.fighter_a.played_this_turn.append(card_by_name("Shove"))
    state.win_source="ringout"
    state.declare_winner(Side.A,"Yorikiri")
    assert state.win_method=="Oshidashi"


def test_classic_power_outcome_unchanged():
    state=setup()
    state.b11_explain_wins=False
    state.declare_winner(Side.A,"Power")
    assert state.win_method=="Power"
