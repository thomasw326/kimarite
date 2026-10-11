"""Designer-approved R21 Search semantics; unit tests do not run gauntlets."""
from types import SimpleNamespace

from kimarite.models import Card
from kimarite.r21_search import (
    REVERSAL_CARD_NAMES,
    search_draw_pile_first,
    search_for_reversal,
)


def _card(n, name):
    return Card(n, name, 0, 0, 0)


def test_search_takes_first_reversal_not_a_later_one():
    cards = [
        _card(11, "Oshi"), _card(12, "Immovable"),
        _card(13, "Pull"), _card(14, "Sidestep"),
    ]
    fighter = SimpleNamespace(draw_pile=list(cards), hand=[_card(99, "Tsuki")])
    original_hand = list(fighter.hand)
    found = search_for_reversal(fighter)

    assert found is cards[1]
    assert fighter.hand == original_hand + [cards[1]]
    assert fighter.draw_pile == [cards[0], cards[2], cards[3]]
    # Not even a shuffle of the untouched three cards.
    assert all(actual is prior for actual, prior in
               zip(fighter.draw_pile, [cards[0], cards[2], cards[3]]))


def test_search_does_not_move_nonmatching_cards_or_choose():
    cards = [
        _card(21, "Oshi"), _card(22, "Harite"),
        _card(23, "Henka"), _card(24, "Nodowa"),
    ]
    fighter = SimpleNamespace(draw_pile=list(cards), hand=[])
    assert search_for_reversal(fighter) is cards[2]
    assert fighter.draw_pile == [cards[0], cards[1], cards[3]]
    assert fighter.hand == [cards[2]]


def test_search_does_nothing_if_no_match():
    cards = [_card(31, "Oshi"), _card(32, "Harite")]
    fighter = SimpleNamespace(draw_pile=list(cards), hand=[])
    assert search_for_reversal(fighter) is None
    assert fighter.draw_pile == cards
    assert fighter.hand == []


def test_search_does_nothing_if_empty():
    fighter = SimpleNamespace(draw_pile=[], hand=[])
    assert search_for_reversal(fighter) is None
    assert fighter.draw_pile == [] and fighter.hand == []


def test_generic_search_is_reusable_and_obeys_draw_order():
    cards = [_card(41, "Pull"), _card(42, "Oshi"), _card(43, "Oshi")]
    fighter = SimpleNamespace(draw_pile=list(cards), hand=[])
    assert search_draw_pile_first(fighter, lambda c: c.name == "Oshi") is cards[1]
    assert fighter.draw_pile == [cards[0], cards[2]]
    assert fighter.hand == [cards[1]]


def test_reversal_classification_matches_r20_successful_reversals():
    assert REVERSAL_CARD_NAMES == frozenset({
        "Henka", "Pull", "Sidestep", "Immovable", "Kannuki"
    })
