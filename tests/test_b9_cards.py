"""B9 regression tests: new cards, stability, generated Okuri, and deck integrity."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from kimarite.catalog import card_by_name
from kimarite.effects import EffectContext, resolve_exchange_effect
from kimarite.kimarite import kimarite_is_satisfied
from kimarite.legality import can_play_card
from kimarite.models import BoutState, FighterState, Side, Wrestler
from kimarite.playing import play_card
from kimarite.rules import gain_push, make_unstable
from kimarite.temporary import add_temporary, remove_temporary, resolve_start_of_turn_temporaries


def state(power_a=7, power_b=6):
    oshi = card_by_name("Oshidashi")
    oshi_basic = card_by_name("Oshi")
    wrestler_a = Wrestler("A", 4, 1, 1, oshi, oshi_basic, oshi_basic)
    wrestler_b = Wrestler("B", 4, 1, 1, oshi, oshi_basic, oshi_basic)
    a = FighterState(wrestler_a, power=power_a)
    b = FighterState(wrestler_b, power=power_b)
    return BoutState(a, b)


def effect(bout, name):
    card = card_by_name(name)
    resolve_exchange_effect(bout, Side.A, card, EffectContext())
    return card


def test_b9_decks_have_fifteen_valid_40_card_lists():
    source = Path(__file__).resolve().parent.parent / "data" / "b9_wrestler_decks.json"
    decks = json.loads(source.read_text(encoding="utf-8"))["decks"]
    assert len(decks) == 15
    for deck in decks.values():
        assert len(deck["cards"]) == 40
        for name in deck["cards"]:
            card_by_name(name)
            assert name not in {"Okuridashi", "Okuritaoshi"}


def test_new_cards_registered_with_orbs():
    expected = {
        "Morotezuki": (3, 0, 0),
        "Kachiage": (3, 0, 0),
        "Nekodamashi": (1, 1, 2),
        "Maesabaki": (0, 2, 1),
        "Deashi": (2, 0, 2),
        "Butsukari": (2, 0, 1),
        "Denshamichi": (1, 0, 2),
        "Spin Away": (0, 1, 2),
    }
    for name, orbs in expected.items():
        card = card_by_name(name)
        assert (card.power, card.technique, card.spirit) == orbs


def test_okuri_finishers_are_generated_only():
    bout = state(8, 6)
    for name in ("Okuridashi", "Okuritaoshi"):
        card = card_by_name(name)
        bout.fighter_a.hand = [card]
        assert not can_play_card(bout, Side.A, card)
    bout.position, bout.momentum = 2, 1
    assert kimarite_is_satisfied(bout, Side.A, card_by_name("Okuridashi"))
    assert kimarite_is_satisfied(bout, Side.A, card_by_name("Okuritaoshi"))
    bout.position = 0
    assert not kimarite_is_satisfied(bout, Side.A, card_by_name("Okuridashi"))
    assert kimarite_is_satisfied(bout, Side.A, card_by_name("Okuritaoshi"))


def test_denshamichi_interruption_creates_okuritaoshi_and_flips_position():
    bout = state()
    card = effect(bout, "Denshamichi")
    assert bout.momentum == 1 and bout.position == 1
    instance = bout.fighter_a.temporary_zone[0]
    assert instance.card == card
    remove_temporary(bout, Side.A, instance, disrupted=True)
    assert bout.position == -1
    assert any(c.name == "Okuritaoshi" for c in bout.fighter_b.kimarite_zone)


def test_spin_away_interruption_creates_okuridashi():
    bout = state()
    effect(bout, "Spin Away")
    assert bout.momentum == 1
    assert bout.side_by_side_owner is Side.A
    instance = bout.fighter_a.temporary_zone[0]
    remove_temporary(bout, Side.A, instance, disrupted=True)
    assert bout.side_by_side_owner is None
    assert any(c.name == "Okuridashi" for c in bout.fighter_b.kimarite_zone)


def test_butsukari_checks_are_independent_and_mills_one():
    bout = state(8, 6)
    bout.momentum = 1
    bout.fighter_a.draw_pile = [card_by_name("Oshi")]
    effect(bout, "Butsukari")
    assert bout.fighter_b.power == 5
    assert bout.fighter_b.unstable
    assert len(bout.fighter_a.discard_pile) == 1
    assert not bout.fighter_a.draw_pile


def test_maesabaki_reduces_grip_and_removes_temporary():
    from kimarite.models import GripState
    bout = state()
    bout.fighter_b.left_grip = GripState.GRIP
    add_temporary(bout, Side.B, card_by_name("Hold Position"), phase="exchange")
    effect(bout, "Maesabaki")
    assert bout.fighter_b.left_grip is GripState.NONE
    assert not bout.fighter_b.temporary_zone


def test_morotezuki_rewards_each_later_card_play():
    bout = state()
    first, second = card_by_name("Morotezuki"), card_by_name("Shove")
    bout.fighter_a.hand = [first, second]
    play_card(bout, Side.A, first)
    assert bout.position == 0
    play_card(bout, Side.A, second)
    assert bout.position >= 2


def test_nekodamashi_unstable_on_play_and_on_survival():
    bout = state()
    card = effect(bout, "Nekodamashi")
    assert bout.fighter_b.unstable
    assert len(bout.fighter_a.temporary_zone) == 1
    bout.fighter_b.unstable = False
    resolve_start_of_turn_temporaries(bout, Side.A)
    assert bout.fighter_b.unstable
    assert not bout.fighter_a.temporary_zone


def test_henka_first_incoming_push_prevented():
    bout = state()
    effect(bout, "Henka")
    gain_push(bout, Side.B, 1)
    assert bout.position == 0
    gain_push(bout, Side.B, 1)
    assert bout.position == -1


def test_kannuki_survives_to_reduce_grips_and_unstable():
    from kimarite.models import GripState
    bout = state()
    bout.fighter_b.left_grip = GripState.DEEP
    bout.fighter_b.right_grip = GripState.GRIP
    effect(bout, "Kannuki")
    resolve_start_of_turn_temporaries(bout, Side.A)
    assert bout.fighter_b.left_grip is GripState.GRIP
    assert bout.fighter_b.right_grip is GripState.NONE
    assert bout.fighter_b.unstable


def test_deashi_zero_one_or_two_independent_push():
    bout = state(8, 7)
    effect(bout, "Deashi")
    assert bout.position == 1  # Power advantage only; Spirit ties.
    bout = state(7, 7)
    effect(bout, "Deashi")
    assert bout.position == 0


def test_pull_no_longer_enters_temporary():
    bout = state()
    bout.position = 1
    bout.fighter_a.draw_pile = [card_by_name("Tsuki")]
    effect(bout, "Pull")
    assert bout.momentum == 1
    assert bout.position == 0
    assert bout.fighter_b.unstable
    assert bout.fighter_a.hand[0].name == "Tsuki"
    assert not bout.fighter_a.temporary_zone


def test_stability_recovers_after_next_affected_turn():
    from kimarite.turns import end_exchange_turn
    bout = state()
    bout.active_side = Side.A
    make_unstable(bout, Side.B)
    assert bout.fighter_b.unstable
    bout.active_side = Side.B
    bout.fighter_b.turns_started = 1
    end_exchange_turn(bout, Side.B)
    assert not bout.fighter_b.unstable


def test_stability_does_not_recover_when_inflicted_during_own_turn():
    from kimarite.turns import end_exchange_turn
    bout = state()
    bout.active_side = Side.A
    bout.fighter_a.turns_started = 1
    make_unstable(bout, Side.A)
    end_exchange_turn(bout, Side.A)
    assert bout.fighter_a.unstable
    bout.active_side = Side.A
    bout.fighter_a.turns_started = 2
    end_exchange_turn(bout, Side.A)
    assert not bout.fighter_a.unstable


def test_repeated_unstable_extends_to_next_affected_turn():
    from kimarite.turns import end_exchange_turn
    bout = state()
    bout.active_side = Side.A
    bout.fighter_a.turns_started = 1
    make_unstable(bout, Side.A)
    bout.fighter_a.turns_started = 2
    make_unstable(bout, Side.A)
    end_exchange_turn(bout, Side.A)
    assert bout.fighter_a.unstable
    bout.fighter_a.turns_started = 3
    end_exchange_turn(bout, Side.A)
    assert not bout.fighter_a.unstable


def test_sukuinage_requires_five_card_hand_advantage():
    bout = state()
    bout.momentum = 2
    bout.fighter_a.hand = [card_by_name("Oshi")] * 5
    bout.fighter_b.hand = [card_by_name("Tsuki")]
    assert not kimarite_is_satisfied(bout, Side.A, card_by_name("Sukuinage"))
    bout.fighter_b.hand = []
    assert kimarite_is_satisfied(bout, Side.A, card_by_name("Sukuinage"))


def test_tottari_requires_opponent_seven_discarded_cards():
    bout = state()
    card = card_by_name("Tottari")
    bout.fighter_a.opponent_grip_reduced_this_turn = True
    bout.fighter_b.discard_pile = [card_by_name("Oshi")] * 6
    assert not kimarite_is_satisfied(bout, Side.A, card)
    bout.fighter_b.discard_pile.append(card_by_name("Tsuki"))
    assert kimarite_is_satisfied(bout, Side.A, card)


def test_kirikaeshi_requires_two_momentum_and_stability():
    bout = state(power_a=4, power_b=8)
    card = card_by_name("Kirikaeshi")
    bout.fighter_b.unstable = True
    bout.momentum = 1
    assert not kimarite_is_satisfied(bout, Side.A, card)
    bout.momentum = 2
    assert kimarite_is_satisfied(bout, Side.A, card)
    bout.fighter_a.unstable = True
    assert not kimarite_is_satisfied(bout, Side.A, card)


def test_tsukiotoshi_requires_unstable_opponent():
    bout = state(power_a=3, power_b=8)
    bout.momentum = 1
    card = card_by_name("Tsukiotoshi")
    assert not kimarite_is_satisfied(bout, Side.A, card)
    bout.fighter_b.unstable = True
    assert kimarite_is_satisfied(bout, Side.A, card)


def test_katasukashi_requires_two_momentum():
    bout = state()
    bout.fighter_a.hand = [card_by_name("Oshi")] * 5
    card = card_by_name("Katasukashi")
    bout.momentum = 1
    assert not kimarite_is_satisfied(bout, Side.A, card)
    bout.momentum = 2
    assert kimarite_is_satisfied(bout, Side.A, card)
