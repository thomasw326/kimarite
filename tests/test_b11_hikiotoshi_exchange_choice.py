"""B11: player chooses Hikiotoshi's looked card, while AI keeps its auto choice."""
from copy import deepcopy

import pytest

from kimarite.b10_web import labelled_choices
from kimarite.catalog import card_by_name
from kimarite.effects import ChoiceRequired, EffectContext
from kimarite.kimarite_effects import resolve_kimarite_play_effect
from kimarite.models import BoutState, FighterState, Side, Wrestler
from kimarite.human_bout import HumanBout


def state_for_hiki():
    blank=card_by_name("Oshi")
    own=FighterState(Wrestler("Human",2,1,0,blank,blank,blank))
    foe=FighterState(Wrestler("Opponent",2,1,0,blank,blank,blank))
    own.draw_pile=[card_by_name(n) for n in ["Tsuki", "Give Ground", "Shiko Stomp", "Oshi"]]
    return BoutState(own,foe)


def test_hikiotoshi_requests_player_choice_without_consuming_draw_pile():
    state=state_for_hiki()
    before=deepcopy(state.fighter_a.draw_pile)
    with pytest.raises(ChoiceRequired) as e:
        resolve_kimarite_play_effect(state,Side.A,card_by_name("Hikiotoshi"),EffectContext(choices={"__human__":True}))
    assert e.value.choice_name=="hikiotoshi_card_index"
    assert e.value.options==[0,1,2]
    assert state.fighter_a.draw_pile==before


def test_hikiotoshi_choice_keeps_selected_card_and_bottoms_rest():
    state=state_for_hiki()
    resolve_kimarite_play_effect(state,Side.A,card_by_name("Hikiotoshi"),EffectContext(choices={"__human__":True,"hikiotoshi_card_index":1}))
    assert [c.name for c in state.fighter_a.hand]==["Give Ground"]
    assert [c.name for c in state.fighter_a.draw_pile]==["Oshi","Tsuki","Shiko Stomp"]


def test_hikiotoshi_choice_labels_show_real_revealed_cards():
    state=state_for_hiki()
    session=type("Session",(),{"state":state,"human_side":Side.A})()
    exc=ChoiceRequired("Hikiotoshi","hikiotoshi_card_index",[0,1,2])
    response=labelled_choices(session,exc)
    assert [o["label"] for o in response["options"]]==["1. Tsuki","2. Give Ground","3. Shiko Stomp"]


def test_hatakikomi_optional_remains_optional():
    state=state_for_hiki()
    with pytest.raises(ChoiceRequired) as e:
        resolve_kimarite_play_effect(state,Side.A,card_by_name("Hatakikomi"),EffectContext(choices={"__human__":True}))
    assert e.value.choice_name=="use_optional"
    resolve_kimarite_play_effect(state,Side.A,card_by_name("Hatakikomi"),EffectContext(choices={"__human__":True,"use_optional":False}))
    assert state.momentum==0
