from kimarite.models import BoutState, Card, FighterState, Side, Stat, Wrestler
from kimarite.tachiai import compare_tachiai
from kimarite.turns import (
    prepare_exchange_deck,
    resolve_first_turn_spirit_reward,
    resolve_turn_card_access,
)


def make_wrestler(
    name: str,
    technique: int,
    spirit: int,
    primary: Stat,
    secondary: Stat,
) -> Wrestler:
    kimarite = Card(1000 + technique + spirit, f"{name} Kimarite")
    prepared = Card(2000 + technique + spirit, f"{name} Prepared")
    top = Card(3000 + technique + spirit, f"{name} Top")
    return Wrestler(
        name,
        0,
        technique,
        spirit,
        kimarite,
        prepared,
        top,
        primary=primary,
        secondary=secondary,
    )


def test_prepared_tachiai_card_goes_to_bottom():
    a = make_wrestler("A", 0, 0, Stat.POWER, Stat.TECHNIQUE)
    b = make_wrestler("B", 0, 0, Stat.POWER, Stat.TECHNIQUE)
    cards = [Card(1, "Top"), Card(2, "Next")]
    bout = BoutState(FighterState(a, draw_pile=list(cards)), FighterState(b))

    prepare_exchange_deck(bout, Side.A)

    assert [card.name for card in bout.fighter_a.draw_pile] == [
        "Top",
        "Next",
        "A Prepared",
    ]


def test_technique_advantage_six_looks_eight_and_keeps_four_on_first_turn():
    a = make_wrestler("A", 6, 0, Stat.TECHNIQUE, Stat.SPIRIT)
    b = make_wrestler("B", 0, 0, Stat.TECHNIQUE, Stat.SPIRIT)
    deck = [
        Card(i, str(i), technique=i % 4, spirit=i % 2)
        for i in range(1, 10)
    ]
    bout = BoutState(FighterState(a, draw_pile=list(deck)), FighterState(b))
    comparison = compare_tachiai(a, b)

    kept = resolve_turn_card_access(bout, Side.A, comparison)

    assert len(kept) == 4
    assert len(bout.fighter_a.hand) == 4
    assert bout.fighter_a.first_exchange_turn is False


def test_losing_technique_first_turn_draws_two_then_next_turn_uses_normal_access():
    a = make_wrestler("A", 0, 0, Stat.POWER, Stat.TECHNIQUE)
    b = make_wrestler("B", 1, 0, Stat.POWER, Stat.TECHNIQUE)
    deck = [Card(i, str(i)) for i in range(1, 7)]
    bout = BoutState(FighterState(a, draw_pile=list(deck)), FighterState(b))
    comparison = compare_tachiai(a, b)

    first = resolve_turn_card_access(bout, Side.A, comparison)
    second = resolve_turn_card_access(bout, Side.A, comparison)

    assert [c.card_id for c in first] == [1, 2]
    assert [c.card_id for c in second] == [3, 4]


def test_spirit_advantage_six_gives_momentum_and_queues_bonus_turn():
    a = make_wrestler("A", 0, 6, Stat.SPIRIT, Stat.POWER)
    b = make_wrestler("B", 0, 0, Stat.SPIRIT, Stat.POWER)
    bout = BoutState(FighterState(a), FighterState(b))
    comparison = compare_tachiai(a, b)

    reward = resolve_first_turn_spirit_reward(bout, Side.A, comparison)

    assert reward == (1, 1)
    assert bout.momentum == 1
    assert bout.fighter_a.bonus_turns_queued == 1
