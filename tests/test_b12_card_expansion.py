"""B12 fifteen-card expansion: direct rules, timing, migration, and UI contract."""
from __future__ import annotations

import pytest

from kimarite.b11_player_draft import AVAILABLE
from kimarite.catalog import card_by_name
from kimarite.effects import EffectContext, EXCHANGE_EFFECTS, draw_one
from kimarite.kimarite import kimarite_is_satisfied
from kimarite.kimarite_effects import resolve_kimarite_play_effect
from kimarite.models import BoutState, Card, FighterState, GripState, Side, Wrestler
from kimarite.playing import play_card
from kimarite.rules import gain_push, reduce_grip
from kimarite.temporary import add_temporary, remove_temporary, resolve_start_of_turn_temporaries


def bout(hand=(), draw=(), opponent_draw=()):
    blank = Card(99999, "B12 test blank")
    a = Wrestler("A", 2, 2, 2, card_by_name("Oshidashi"),
                 card_by_name("Oshi"), card_by_name("Oshi"))
    b = Wrestler("B", 2, 2, 2, card_by_name("Oshidashi"),
                 card_by_name("Oshi"), card_by_name("Oshi"))
    state = BoutState(
        FighterState(a, hand=list(hand), draw_pile=list(draw)),
        FighterState(b, draw_pile=list(opponent_draw)),
        active_side=Side.A,
        turn_number=1,
    )
    state.fighter_a.plays_remaining = 5
    state.fighter_b.plays_remaining = 5
    return state, blank


EXPECTED = {
    "Sonkyo": (1, 1, 1),
    "Renzoku": (0, 3, 0), "Meguri": (0, 2, 1),
    "Nokotta!": (1, 0, 2), "Hakkeyoi!": (0, 0, 3),
    "Hazuoshi": (1, 1, 1), "Inashi": (1, 1, 2),
    "Chiri-chozu": (1, 3, 1), "Shikiri": (1, 2, 2),
    "Shiko Stomp": (1, 0, 4),
    "Kubinage": (2, 0, 1), "Kimedashi": (2, 0, 1),
    "Kimetaoshi": (3, 0, 0),
    "Reckless Charge": (0, 0, 3), "Sheer Grit": (0, 0, 3),
}


def test_fifteen_names_and_orbs_registered_for_draft_and_engine():
    for name, orbs in EXPECTED.items():
        card = card_by_name(name)
        assert (card.power, card.technique, card.spirit) == orbs
        assert name in AVAILABLE
        if name not in {"Sonkyo", "Kubinage", "Kimedashi", "Kimetaoshi"}:
            assert name in EXCHANGE_EFFECTS


def test_sonkyo_and_new_shiko_are_distinct():
    assert card_by_name("Sonkyo").card_id == 17
    assert card_by_name("Shiko Stomp").card_id != 17
    state, _ = bout(hand=[card_by_name("Shiko Stomp")])
    state.fighter_a.power = 5
    state.fighter_b.power = 4
    state.momentum = 1
    play_card(state, Side.A, state.fighter_a.hand[0])
    assert (state.position, state.momentum, state.fighter_a.power) == (1, 2, 6)
    assert not state.fighter_a.temporary_zone
    assert [c.name for c in state.fighter_a.discard_pile] == ["Shiko Stomp"]


@pytest.mark.parametrize("advantage,mill", [(0,0),(1,1),(2,1),(3,2),(4,2),(5,3)])
def test_kubinage_mills_by_rounded_up_power_lead(advantage, mill):
    state, blank = bout(opponent_draw=[blank_card() for _ in range(8)])
    state.fighter_a.power = advantage
    state.fighter_b.power = 0
    resolve_kimarite_play_effect(state, Side.A, card_by_name("Kubinage"), EffectContext())
    assert len(state.fighter_b.discard_pile) == mill


def blank_card():
    return Card(99000, "Blank")


def test_kubinage_wins_at_fifteen_discarded():
    state, blank = bout()
    state.fighter_b.discard_pile = [blank] * 14
    assert not kimarite_is_satisfied(state, Side.A, card_by_name("Kubinage"))
    state.fighter_b.discard_pile.append(blank)
    assert kimarite_is_satisfied(state, Side.A, card_by_name("Kubinage"))


def test_kimedashi_stacks_two_power_reductions_and_position_requirement():
    state, blank = bout()
    state.position = 1
    state.fighter_a.power = 6
    state.fighter_b.power = 4
    resolve_kimarite_play_effect(state, Side.A, card_by_name("Kimedashi"), EffectContext())
    assert state.fighter_b.power == 2
    assert not kimarite_is_satisfied(state, Side.A, card_by_name("Kimedashi"))
    state.position = 2
    assert kimarite_is_satisfied(state, Side.A, card_by_name("Kimedashi"))
    state.fighter_b.left_grip = GripState.GRIP
    assert not kimarite_is_satisfied(state, Side.A, card_by_name("Kimedashi"))


@pytest.mark.parametrize("grip,mill", [(0,4),(1,3),(2,2),(3,1),(4,0)])
def test_kimetaoshi_mill_scales_with_opponent_grip(grip, mill):
    state, _ = bout(opponent_draw=[blank_card() for _ in range(6)])
    state.fighter_b.left_grip = GripState(min(grip, 2))
    state.fighter_b.right_grip = GripState(max(0, grip-2))
    resolve_kimarite_play_effect(state, Side.A, card_by_name("Kimetaoshi"), EffectContext())
    assert len(state.fighter_b.discard_pile) == mill


def test_kimetaoshi_uses_ten_discard_and_power_lead_four():
    state, blank = bout()
    state.fighter_a.power = 6
    state.fighter_b.power = 2
    state.fighter_b.discard_pile = [blank] * 9
    assert not kimarite_is_satisfied(state, Side.A, card_by_name("Kimetaoshi"))
    state.fighter_b.discard_pile.append(blank)
    assert kimarite_is_satisfied(state, Side.A, card_by_name("Kimetaoshi"))
    state.fighter_a.left_grip = GripState.GRIP
    assert not kimarite_is_satisfied(state, Side.A, card_by_name("Kimetaoshi"))


def test_nokotta_backward_gains_two_push():
    state, _ = bout(hand=[card_by_name("Nokotta!")])
    state.position = -2
    play_card(state, Side.A, state.fighter_a.hand[0])
    assert state.position == 0


def test_hazuoshi_only_disrupts_after_two_preceding_cards():
    state, _ = bout(hand=[card_by_name("Renzoku"),
                           card_by_name("Sheer Grit"), card_by_name("Hazuoshi")])
    state.fighter_b.left_grip = GripState.GRIP
    play_card(state, Side.A, card_by_name("Renzoku"))
    play_card(state, Side.A, card_by_name("Sheer Grit"))
    play_card(state, Side.A, card_by_name("Hazuoshi"))
    assert state.fighter_b.unstable
    assert state.fighter_b.left_grip is GripState.NONE


def test_renzoku_rewards_subsequent_draws():
    state, blank = bout(hand=[card_by_name("Renzoku"),card_by_name("Meguri")],
                        draw=[blank_card()] * 3)
    state.fighter_a.plays_remaining = 2
    play_card(state, Side.A, card_by_name("Renzoku"))
    assert state.fighter_a.plays_remaining == 1
    play_card(state, Side.A, card_by_name("Meguri"))
    assert state.fighter_a.plays_remaining == 2
    assert len(state.fighter_a.hand) == 2


def test_meguri_redirects_discard_and_is_exhausted_by_opponent_push():
    state, blank = bout(hand=[card_by_name("Meguri"),card_by_name("Nokotta!")],
                        draw=[blank_card()] * 3)
    play_card(state, Side.A, card_by_name("Meguri"))
    play_card(state, Side.A, card_by_name("Nokotta!"))
    assert state.fighter_a.draw_pile[-1].name == "Nokotta!"
    assert any(t.card.name == "Meguri" for t in state.fighter_a.temporary_zone)
    gain_push(state, Side.B, 2)
    assert not any(t.card.name == "Meguri" for t in state.fighter_a.temporary_zone)
    assert any(c.name == "Meguri" for c in state.fighter_a.exhaust_pile)


def test_hakkeyoi_later_plays_and_opponent_third_card():
    r1 = Card(99001, "Renzoku")
    r2 = Card(99002, "Renzoku")
    state, _ = bout(hand=[card_by_name("Hakkeyoi!"),r1,r2])
    play_card(state, Side.A, card_by_name("Hakkeyoi!"))
    play_card(state, Side.A, r1)
    play_card(state, Side.A, r2)
    assert state.momentum == 2
    state.active_side = Side.B
    state.fighter_b.hand = [Card(99003+i, "Renzoku") for i in range(3)]
    for card in list(state.fighter_b.hand):
        play_card(state, Side.B, card)
    assert state.momentum == 1
    resolve_start_of_turn_temporaries(state, Side.A)
    assert not any(t.card.name == "Hakkeyoi!" for t in state.fighter_a.temporary_zone)


def test_inashi_recycles_one_card_stabilises_and_delays_momentum():
    state, blank = bout(hand=[card_by_name("Inashi")])
    state.fighter_a.discard_pile = [blank]
    state.fighter_a.unstable = True
    state.momentum = 1
    play_card(state, Side.A, card_by_name("Inashi"))
    assert state.momentum == 0
    assert state.fighter_a.hand == [blank]
    assert not state.fighter_a.unstable
    assert state.fighter_a.power == 1
    resolve_start_of_turn_temporaries(state, Side.A)
    assert state.momentum == 2


def test_chiri_chozu_draws_once_per_turn_for_successful_temporary():
    state, blank = bout(draw=[blank_card()] * 3)
    add_temporary(state, Side.A, card_by_name("Chiri-chozu"), phase="exchange")
    add_temporary(state, Side.A, card_by_name("Immovable"), phase="exchange")
    resolve_start_of_turn_temporaries(state, Side.A)
    assert len(state.fighter_a.hand) == 1
    add_temporary(state, Side.A, card_by_name("Immovable"), phase="exchange")
    resolve_start_of_turn_temporaries(state, Side.A)
    assert len(state.fighter_a.hand) == 1


def test_shikiri_draws_once_per_turn_from_grip_and_destruction():
    state, blank = bout(draw=[blank_card()] * 3)
    add_temporary(state, Side.A, card_by_name("Shikiri"), phase="exchange")
    state.fighter_b.left_grip = GripState.GRIP
    reduce_grip(state, Side.B)
    assert len(state.fighter_a.hand) == 1
    target = add_temporary(state, Side.B, card_by_name("Immovable"), phase="exchange")
    remove_temporary(state, Side.B, target, disrupted=True)
    assert len(state.fighter_a.hand) == 1
    state.turn_number += 1
    target = add_temporary(state, Side.B, card_by_name("Immovable"), phase="exchange")
    remove_temporary(state, Side.B, target, disrupted=True)
    assert len(state.fighter_a.hand) == 2


def test_reckless_charge_recoil_on_survival_and_early_destruction():
    for disrupted in (False, True):
        state, _ = bout(hand=[card_by_name("Reckless Charge")])
        play_card(state, Side.A, card_by_name("Reckless Charge"))
        assert (state.position, state.momentum) == (2, 1)
        instance = state.fighter_a.temporary_zone[0]
        if disrupted:
            remove_temporary(state, Side.A, instance, disrupted=True)
        else:
            resolve_start_of_turn_temporaries(state, Side.A)
        assert (state.position, state.momentum) == (1, 0)
        assert not state.fighter_a.temporary_zone


def test_sheer_grit_uses_exhausted_discard_threshold_seven():
    for discarded in (6, 7, 10):
        state, blank = bout(hand=[card_by_name("Sheer Grit")])
        state.fighter_a.discard_pile = [blank] * discarded
        play_card(state, Side.A, card_by_name("Sheer Grit"))
        assert state.momentum == (1 if discarded < 7 else 2)
        assert state.position == (0 if discarded < 7 else 1)


def test_kubinage_prepared_tachiai_mills_before_exchange():
    from kimarite.tachiai import compare_tachiai
    from kimarite.tachiai_effects import resolve_prepared_tachiai
    kubinage = card_by_name("Kubinage")
    blank = blank_card()
    a = Wrestler("A", 5, 0, 1, kubinage, kubinage, blank)
    b = Wrestler("B", 0, 0, 0, blank, blank, blank)
    state = BoutState(
        FighterState(a, draw_pile=[blank] * 6, power=5),
        FighterState(b, draw_pile=[blank] * 6, power=0),
    )
    # Explicit B11 player commits put prepared Kimarite in the zone;
    # Classic one-card preparation instead returns it to the draw pile.
    resolve_prepared_tachiai(
        state, compare_tachiai(a, b),
        committed_cards={Side.A: (kubinage,), Side.B: (blank,)},
    )
    assert len(state.fighter_b.discard_pile) == 3
    assert any(card.name == "Kubinage" for card in state.fighter_a.kimarite_zone)


def test_chiri_and_shikiri_prepared_tachiai_enter_persistent_temporaries():
    from kimarite.tachiai import compare_tachiai
    from kimarite.tachiai_effects import resolve_prepared_tachiai
    chiri = card_by_name("Chiri-chozu")
    shikiri = card_by_name("Shikiri")
    blank = blank_card()
    a = Wrestler("A", 2, 2, 2, blank, chiri, blank)
    b = Wrestler("B", 2, 2, 2, blank, blank, blank)
    state = BoutState(FighterState(a), FighterState(b))
    resolve_prepared_tachiai(
        state, compare_tachiai(a, b),
        committed_cards={Side.A: (chiri, shikiri), Side.B: (blank,)},
    )
    assert {x.card.name for x in state.fighter_a.temporary_zone} == {
        "Chiri-chozu", "Shikiri"
    }
    resolve_start_of_turn_temporaries(state, Side.A)
    assert {x.card.name for x in state.fighter_a.temporary_zone} == {
        "Chiri-chozu", "Shikiri"
    }


def test_approved_henka_and_explosive_step_orb_nerfs():
    henka = card_by_name("Henka")
    explosive = card_by_name("Explosive Step — Fumikomi")
    assert (henka.power, henka.technique, henka.spirit) == (0, 2, 0)
    assert (explosive.power, explosive.technique, explosive.spirit) == (0, 0, 2)
