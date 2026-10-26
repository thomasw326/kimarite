"""Exhaustive small-deck equivalence: old Classic Oshi reveal vs B11 planner.

The baseline is deliberately expressed independently of the new planner.
"""
from itertools import product

from kimarite.catalog import card_by_name
from kimarite.b11_tachiai_reveals import plan_reveals

NAMES = ("Oshi", "Tsuki", "Shove", "Harite")


def classic_reference(prepared_name, cards):
    remaining = list(cards)
    revealed = []
    if prepared_name in ("Oshi", "Tsuki"):
        while remaining:
            card = remaining.pop(0)
            revealed.append(card)
            if card.name not in ("Oshi", "Tsuki"):
                break
    return revealed, remaining


def test_legacy_equivalence_for_all_sequences_to_four_cards():
    for prepared in NAMES:
        for length in range(5):
            for names in product(NAMES, repeat=length):
                deck = [card_by_name(name) for name in names]
                expected_revealed, expected_remaining = classic_reference(prepared, deck)
                actual = plan_reveals((card_by_name(prepared),), deck)
                assert actual.revealed == tuple(expected_revealed), (prepared, names)
                assert actual.remaining == tuple(expected_remaining), (prepared, names)
                assert actual.orbs == (
                    sum(c.power for c in expected_revealed),
                    sum(c.technique for c in expected_revealed),
                    sum(c.spirit for c in expected_revealed),
                ), (prepared, names)
                assert [id(c) for c in (*actual.revealed, *actual.remaining)] == [
                    id(c) for c in deck
                ]


def test_two_committed_oshi_chains_do_not_duplicate_physical_cards():
    deck = [card_by_name(n) for n in NAMES * 2]
    actual = plan_reveals((card_by_name("Oshi"), card_by_name("Oshi")), deck)
    assert len(actual.revealed) + len(actual.remaining) == len(deck)
    assert {id(c) for c in actual.revealed}.isdisjoint(
        {id(c) for c in actual.remaining}
    )
