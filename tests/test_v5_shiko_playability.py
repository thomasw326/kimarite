"""Regression: Shiko Stomp must be a playable persistent defense, not a buff."""

from kimarite.ai import candidate_plays
from kimarite.catalog import card_by_name
from kimarite.effects import TEMPORARY_CARD_NAMES
from kimarite.models import BoutState, FighterState, Side, Wrestler
from kimarite.playing import play_card
from kimarite.style_ai_v5 import choose_style_play, play_style_turn
from kimarite.tachiai import compare_tachiai
from kimarite.temporary import resolve_start_of_turn_temporaries


def shiko_state():
    starting = card_by_name("Oshidashi")
    oshi = card_by_name("Oshi")
    shiko = card_by_name("Shiko Stomp")
    harite = card_by_name("Harite")
    a = Wrestler("A", 2, 2, 2, starting, oshi, oshi)
    b = Wrestler("B", 2, 2, 2, starting, oshi, oshi)
    state = BoutState(
        FighterState(a, hand=[shiko], draw_pile=[oshi]),
        FighterState(b, hand=[harite], draw_pile=[oshi]),
        active_side=Side.A,
    )
    state.fighter_a.plays_remaining = 1
    state.fighter_b.plays_remaining = 1
    return state, compare_tachiai(a, b)


def test_shiko_stomp_exchange_play_is_legal_and_persistent():
    state, _ = shiko_state()
    shiko = state.fighter_a.hand[0]
    assert shiko.name in TEMPORARY_CARD_NAMES
    power_before = state.fighter_a.power

    play_card(state, Side.A, shiko)
    assert state.fighter_a.plays_remaining == 0  # No +1 Play buff.
    assert state.fighter_a.power == power_before  # No stat buff.
    assert [t.card.name for t in state.fighter_a.temporary_zone] == ["Shiko Stomp"]
    assert not any(c.name == "Shiko Stomp" for c in state.fighter_a.discard_pile)

    resolve_start_of_turn_temporaries(state, Side.A)
    assert [t.card.name for t in state.fighter_a.temporary_zone] == ["Shiko Stomp"]

    # It prevents one opposing negative effect, then is consumed as designed.
    state.active_side = Side.B
    play_card(state, Side.B, state.fighter_b.hand[0])
    assert state.fighter_a.power == power_before
    assert not state.fighter_a.temporary_zone
    assert any(c.name == "Shiko Stomp" for c in state.fighter_a.discard_pile)


def test_shiko_stomp_visible_to_tactical_and_style_ai():
    state, comparison = shiko_state()

    options = candidate_plays(state, Side.A, comparison)
    assert any(option.card.name == "Shiko Stomp" for option in options)

    for style in ("Pressure Fighter", "The Technician", None):
        choice = choose_style_play(state, Side.A, comparison, style)
        assert choice is not None and choice.card.name == "Shiko Stomp"
    assert not state.card_plays  # Candidate evaluations are non-mutating.

    played = play_style_turn(state, Side.A, comparison, "Pressure Fighter")
    assert played == ["Shiko Stomp"]
    assert [t.card.name for t in state.fighter_a.temporary_zone] == ["Shiko Stomp"]
    assert state.fighter_a.plays_remaining == 0
