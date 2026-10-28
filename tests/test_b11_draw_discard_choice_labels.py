"""Card choices must describe the transactional post-effect hand, not stale hand slots."""
import pytest

from kimarite.actions import submit_card_action
from kimarite.b10_web import labelled_choices
from kimarite.catalog import card_by_name
from kimarite.effects import ChoiceRequired
from kimarite.models import BoutState, FighterState, Side, Wrestler


def bout(card_name):
    blank=card_by_name("Oshi")
    human=FighterState(Wrestler("Human",2,1,0,blank,blank,blank))
    other=FighterState(Wrestler("Other",2,1,0,blank,blank,blank))
    human.hand=[card_by_name(card_name),card_by_name("Tsuki"),card_by_name("Give Ground"),card_by_name("Shiko Stomp")]
    human.draw_pile=[card_by_name("Salt Throw"),card_by_name("Regain Balance")]
    human.plays_remaining=3
    state=BoutState(human,other)
    state.active_side=Side.A
    return state


@pytest.mark.parametrize("name",["Pull","Tsukitaoshi"])
def test_draw_then_discard_has_four_named_choices_and_preserves_state(name):
    state=bout(name)
    before_hand=list(state.fighter_a.hand)
    before_draw=list(state.fighter_a.draw_pile)
    with pytest.raises(ChoiceRequired) as raised:
        submit_card_action(state,Side.A,0)
    exc=raised.value
    assert exc.choice_name=="hand_index"
    assert exc.options==[0,1,2,3]
    assert [c.name for c in exc.visible_cards]==["Tsuki","Give Ground","Shiko Stomp","Salt Throw"]
    session=type("Session",(),{"state":state,"human_side":Side.A})()
    data=labelled_choices(session,exc,{"hand_index":0})
    assert [x["label"] for x in data["options"]]==[
        "1. Tsuki","2. Give Ground","3. Shiko Stomp","4. Salt Throw"]
    assert [x["card"]["name"] for x in data["options"]]==[
        "Tsuki","Give Ground","Shiko Stomp","Salt Throw"]
    assert state.fighter_a.hand==before_hand
    assert state.fighter_a.draw_pile==before_draw
    submit_card_action(state,Side.A,0,choices={"hand_index":3})
    assert "Salt Throw" in [c.name for c in state.fighter_a.discard_pile]
    assert "Salt Throw" not in [c.name for c in state.fighter_a.hand]


def test_existing_hand_discard_labels_match_post_play_indices():
    state=bout("Tsuppari")
    # A standalone Tsuppari won't chain, so use one of the guaranteed
    # draw-then-discard effects above to test indexed choices.
    state=bout("Pull")
    with pytest.raises(ChoiceRequired) as raised:
        submit_card_action(state,Side.A,0)
    data=labelled_choices(type("Session",(),{"state":state,"human_side":Side.A})(),raised.value,{"hand_index":0})
    assert all("Option" not in item["label"] for item in data["options"])
