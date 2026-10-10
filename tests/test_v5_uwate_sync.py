"""Uwate current-print-pool selection and free follow-up."""
from kimarite.catalog import card_by_name
from kimarite.effects import EffectContext
from kimarite.models import BoutState, FighterState, GripState, Side, Wrestler
from kimarite.playing import play_card


def bout():
    starter = card_by_name("Oshidashi")
    a = Wrestler("A", 2, 2, 2, starter, starter, starter)
    b = Wrestler("B", 2, 2, 2, starter, starter, starter)
    return BoutState(
        FighterState(a, hand=[card_by_name("Uwate")],
                     draw_pile=[card_by_name("Shove"), card_by_name("Tsuri")]),
        FighterState(b, power=3),
        active_side=Side.A,
    )


def test_uwate_without_deep_grip_looks_and_draws():
    state = bout()
    play_card(state, Side.A, state.fighter_a.hand[0])
    assert state.fighter_a.left_grip is GripState.GRIP
    assert state.fighter_a.plays_remaining == 1
    assert [c.name for c in state.fighter_a.hand] == ["Tsuri"]
    assert [c.name for c in state.fighter_a.draw_pile] == ["Shove"]
    assert [c.card.name for c in state.fighter_a.temporary_zone] == ["Uwate"]


def test_uwate_deep_grip_plays_selected_card_free():
    state = bout()
    state.fighter_a.left_grip = GripState.GRIP
    play_card(state, Side.A, state.fighter_a.hand[0],
              context=EffectContext(choices={"uwate_card_index": 0}))
    assert state.fighter_a.left_grip is GripState.DEEP
    assert state.fighter_a.plays_remaining == 1
    assert state.fighter_a.cards_played_this_turn == 2
    assert state.card_plays == [(Side.A, "Uwate"), (Side.A, "Belt Slap")]
    assert [c.card.name for c in state.fighter_a.temporary_zone] == ["Uwate"]
