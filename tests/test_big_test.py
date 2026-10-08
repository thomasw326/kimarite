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


def test_every_pool_card_is_legal_as_prepared_tachiai():
    """All cards contribute stats; only cards with phase text add phase effects."""
    from dataclasses import replace
    from kimarite.catalog import CARD_POOL
    from kimarite.models import BoutState, FighterState
    from kimarite.tachiai import compare_tachiai
    from kimarite.tachiai_effects import resolve_prepared_tachiai

    base = make_fighter(roster()[0], random.Random(42), 1).wrestler
    foe = make_fighter(roster()[1], random.Random(13), 2).wrestler
    for card in CARD_POOL:
        first = replace(base, prepared_tachiai_card=card)
        state = BoutState(
            FighterState(first, draw_pile=list(CARD_POOL)),
            FighterState(foe, draw_pile=list(CARD_POOL)),
        )
        comparison = compare_tachiai(first, foe)
        resolve_prepared_tachiai(state, comparison)
