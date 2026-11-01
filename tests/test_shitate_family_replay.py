"""B11 Shitate specialist finishers, Recover and discard replay/Exhaust safety."""
from copy import deepcopy

import pytest

from kimarite.actions import submit_card_action
from kimarite.ai import candidate_plays
from kimarite.catalog import card_by_name
from kimarite.effects import ChoiceRequired, EffectContext
from kimarite.kimarite import kimarite_is_satisfied
from kimarite.models import BoutState, FighterState, GripState, Side, TemporaryInstance, Wrestler
from kimarite.play_human import CARD_LIBRARY_TEXT
from kimarite.playing import play_card
from kimarite.prevention import prevent_negative_effect
from kimarite.rules import gain_push, recover_momentum, recover_push
from kimarite.temporary import remove_temporary, resolve_start_of_turn_temporaries


def state_with(*, card="Shitatehineri", discard=(), deep=True, pos=0, mom=0, draw=()):
    starter = card_by_name("Yorikiri")
    a = Wrestler("A", 2, 2, 2, starter, starter, starter)
    b = Wrestler("B", 2, 2, 2, starter, starter, starter)
    return BoutState(
        FighterState(
            a, hand=[card_by_name(card)],
            draw_pile=[card_by_name(name) for name in draw],
            discard_pile=[card_by_name(name) for name in discard],
            right_grip=GripState.DEEP if deep else GripState.GRIP,
        ),
        FighterState(b, power=3),
        position=pos, momentum=mom, active_side=Side.A,
    )


def test_shitate_family_catalog_and_tooltips():
    for name in ("Shitatedashinage", "Shitatehineri"):
        card = card_by_name(name)
        assert card.is_kimarite
        assert (card.power, card.technique, card.spirit) == (0, 2, 1)
        assert name.casefold() in CARD_LIBRARY_TEXT
    assert "Exhaust" in CARD_LIBRARY_TEXT["shitatehineri"]["notes"]
    assert "Recover" in CARD_LIBRARY_TEXT["shitatedashinage"]["notes"]


def test_shitatehineri_win_requires_deep_usable_superior_grip_stability_and_no_temp():
    card = card_by_name("Shitatehineri")
    state = state_with()
    assert kimarite_is_satisfied(state, Side.A, card)
    state.fighter_b.right_grip = GripState.DEEP
    assert not kimarite_is_satisfied(state, Side.A, card)  # equal total Grip
    state.fighter_a.left_grip = GripState.GRIP
    assert kimarite_is_satisfied(state, Side.A, card)
    state.fighter_a.unstable = True
    assert not kimarite_is_satisfied(state, Side.A, card)
    state.fighter_a.unstable = False
    state.fighter_b.temporary_zone.append(
        TemporaryInstance(card_by_name("Hold Position"), 0, "exchange")
    )
    assert not kimarite_is_satisfied(state, Side.A, card)
    state.fighter_b.temporary_zone.clear()
    state.fighter_a.right_grip = GripState.GRIP
    assert not kimarite_is_satisfied(state, Side.A, card)


def test_shitatedashinage_requires_unstable_deep_right_nonnegative_momentum():
    card = card_by_name("Shitatedashinage")
    state = state_with(card="Shitatedashinage")
    state.fighter_b.unstable = True
    assert kimarite_is_satisfied(state, Side.A, card)
    state.momentum = -1
    assert not kimarite_is_satisfied(state, Side.A, card)
    state.momentum = 0
    state.fighter_a.right_grip = GripState.GRIP
    assert not kimarite_is_satisfied(state, Side.A, card)
    state.fighter_a.right_grip = GripState.DEEP
    state.fighter_b.unstable = False
    assert not kimarite_is_satisfied(state, Side.A, card)


def test_recover_keyword_clamps_at_zero_for_both_sides():
    s = state_with(pos=-2, mom=-2)
    recover_push(s, Side.A, 8)
    recover_momentum(s, Side.A, 8)
    assert (s.position, s.momentum) == (0, 0)
    recover_push(s, Side.A, 1)
    recover_momentum(s, Side.A, 1)
    assert (s.position, s.momentum) == (0, 0)
    s.position, s.momentum = 2, 2
    recover_push(s, Side.B, 1)
    recover_momentum(s, Side.B, 1)
    assert (s.position, s.momentum) == (1, 1)


def test_shitatedashinage_recovers_negative_tracks_and_draws_under_deep_right():
    s = state_with(card="Shitatedashinage", pos=-2, mom=-2, draw=("Shove",))
    play_card(s, Side.A, s.fighter_a.hand[0])
    assert (s.position, s.momentum) == (-1, -1)
    assert [c.name for c in s.fighter_a.hand] == ["Shove"]
    assert s.fighter_a.plays_remaining == 1


def test_shitatedashinage_does_not_draw_or_recover_without_deep_grip():
    s = state_with(card="Shitatedashinage", pos=-2, mom=-2, draw=("Shove",), deep=False)
    play_card(s, Side.A, s.fighter_a.hand[0])
    assert (s.position, s.momentum) == (-2, -2)
    assert not s.fighter_a.hand
    assert [c.name for c in s.fighter_a.draw_pile] == ["Shove"]


def test_shitatedashinage_draw_is_conditional_on_grip_not_negative_tracks():
    s = state_with(card="Shitatedashinage", pos=1, mom=1, draw=("Shove",))
    play_card(s, Side.A, s.fighter_a.hand[0])
    assert (s.position, s.momentum) == (1, 1)
    assert [c.name for c in s.fighter_a.hand] == ["Shove"]


def test_human_replay_selection_is_transactional_and_exhausts_free_play():
    s = state_with(discard=("Shove", "Gain Right Grip"))
    before = deepcopy(s)
    with pytest.raises(ChoiceRequired) as err:
        submit_card_action(s, Side.A, 0)
    assert err.value.choice_name == "replay_discard_index"
    assert err.value.options == [0, 1]
    assert s == before
    submit_card_action(s, Side.A, 0, choices={"replay_discard_index": 0})
    assert s.position == 1
    assert s.fighter_a.plays_remaining == 1  # Shitatehineri costs a Play; replay is free
    assert s.fighter_a.cards_played_this_turn == 2
    assert s.card_plays == [(Side.A, "Shitatehineri"), (Side.A, "Shove")]
    assert [c.name for c in s.fighter_a.exhaust_pile] == ["Shove"]
    assert not s.fighter_a.discard_pile
    assert [c.name for c in s.fighter_a.kimarite_zone] == ["Shitatehineri"]


def test_shitatehineri_without_deep_right_does_not_replay_or_exhaust():
    s = state_with(deep=False, discard=("Shove",))
    play_card(s, Side.A, s.fighter_a.hand[0])
    assert s.card_plays == [(Side.A, "Shitatehineri")]
    assert [c.name for c in s.fighter_a.discard_pile] == ["Shove"]
    assert not s.fighter_a.exhaust_pile


def test_replayed_kimarite_has_on_play_effect_but_not_persistent_zone():
    s = state_with(discard=("Yorikiri",))
    play_card(s, Side.A, s.fighter_a.hand[0])
    assert s.position == 1  # Yorikiri grants Push with total Grip at least 2
    assert [c.name for c in s.fighter_a.kimarite_zone] == ["Shitatehineri"]
    assert [c.name for c in s.fighter_a.exhaust_pile] == ["Yorikiri"]


def test_replayed_temporary_survives_for_delayed_effect_then_exhausts():
    s = state_with(discard=("Attempt Deep Inside Grip",))
    play_card(s, Side.A, s.fighter_a.hand[0])
    assert not s.fighter_a.exhaust_pile
    assert len(s.fighter_a.temporary_zone) == 1
    assert s.fighter_a.temporary_zone[0].exhaust_on_leave
    resolve_start_of_turn_temporaries(s, Side.A)
    assert not s.fighter_a.temporary_zone
    assert [c.name for c in s.fighter_a.exhaust_pile] == ["Attempt Deep Inside Grip"]
    assert not s.fighter_a.discard_pile


def test_replayed_temporary_exhausts_after_disruption_with_normal_penalty():
    s = state_with(discard=("Attempt Deep Inside Grip",))
    play_card(s, Side.A, s.fighter_a.hand[0])
    instance = s.fighter_a.temporary_zone[0]
    remove_temporary(s, Side.A, instance, disrupted=True)
    assert s.momentum == -1  # opponent gains 1 Momentum on disruption
    assert [c.name for c in s.fighter_a.exhaust_pile] == ["Attempt Deep Inside Grip"]
    assert not s.fighter_a.discard_pile


def test_replayed_shiko_stomp_stays_active_then_exhausts_when_consumed():
    s = state_with(discard=("Shiko Stomp",))
    play_card(s, Side.A, s.fighter_a.hand[0])
    assert s.fighter_a.temporary_zone[0].exhaust_on_leave
    assert prevent_negative_effect(s, Side.A, source="test", description="test")
    assert not s.fighter_a.temporary_zone
    assert [c.name for c in s.fighter_a.exhaust_pile] == ["Shiko Stomp"]


def test_replayed_grip_shield_exhausts_when_push_is_prevented():
    s = state_with(discard=("Gain Right Grip",))
    play_card(s, Side.A, s.fighter_a.hand[0])
    gain_push(s, Side.B, 1)
    assert s.position == 0
    assert not s.fighter_a.temporary_zone
    assert [c.name for c in s.fighter_a.exhaust_pile] == ["Gain Right Grip"]


def test_replay_another_shitatehineri_does_not_duplicate_or_loop():
    s = state_with(discard=("Shitatehineri", "Shove"))
    play_card(s, Side.A, s.fighter_a.hand[0],
              context=EffectContext(choices={"replay_discard_index": 0}))
    assert s.card_plays == [
        (Side.A, "Shitatehineri"),
        (Side.A, "Shitatehineri"),
        (Side.A, "Shove"),
    ]
    assert sorted(c.name for c in s.fighter_a.exhaust_pile) == [
        "Shitatehineri", "Shove"
    ]
    assert not s.fighter_a.discard_pile
    assert s.fighter_a.plays_remaining == 1


def test_ai_considers_each_replay_target():
    s = state_with(discard=("Shove", "Yorikiri"))
    options = [
        play for play in candidate_plays(s, Side.A, None)
        if play.card.name == "Shitatehineri"
    ]
    assert len(options) == 2
    assert {play.context.choice("replay_discard_index") for play in options} == {0, 1}
