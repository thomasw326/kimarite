import random
from collections import Counter

from scripts.big_test import STAT_BUILDS, make_fighter, roster
from kimarite.models import Stat


def test_108_unique_configs():
    configs = roster()
    assert len(STAT_BUILDS) == 18
    assert len(configs) == 108
    assert len(set(name for name, _, _ in configs)) == 108
    assert all(sum(stats) == 5 for stats in STAT_BUILDS)


def test_random_card_assignments_are_independent_and_reproducible():
    configs = roster()
    a = make_fighter(configs[0], random.Random(321), 1)
    b = make_fighter(configs[-1], random.Random(321), 1)
    assert a.wrestler.starting_kimarite == b.wrestler.starting_kimarite
    assert a.wrestler.prepared_tachiai_card == b.wrestler.prepared_tachiai_card
    assert a.wrestler.top_of_deck_card == b.wrestler.top_of_deck_card
    assert len(a.draw_pile) == len(b.draw_pile)
    assert a.draw_pile == b.draw_pile


def test_card_positions_are_distinct_and_reproducible():
    fighter = make_fighter(roster()[0], random.Random(12345), 1)
    w = fighter.wrestler
    assert w.starting_kimarite.is_kimarite
    assert w.prepared_tachiai_card.card_id != w.top_of_deck_card.card_id
    assert fighter.draw_pile[0] == w.top_of_deck_card
    assert w.prepared_tachiai_card not in fighter.draw_pile
