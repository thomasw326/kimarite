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


def test_technique_advantage_six_looks_eight_and_keeps_five_on_first_turn():
    a = make_wrestler("A", 6, 0, Stat.TECHNIQUE, Stat.SPIRIT)
    b = make_wrestler("B", 0, 0, Stat.TECHNIQUE, Stat.SPIRIT)
    deck = [
        Card(i, str(i), technique=i % 4, spirit=i % 2)
        for i in range(1, 10)
    ]
    bout = BoutState(FighterState(a, draw_pile=list(deck)), FighterState(b))
    comparison = compare_tachiai(a, b)

    kept = resolve_turn_card_access(bout, Side.A, comparison)

    assert len(kept) == 5
    assert len(bout.fighter_a.hand) == 5
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


def test_spirit_momentum_resolves_before_start_kimarite_check():
    kimarite = Card(5000, "Yorikiri", power=1, technique=1, spirit=1, is_kimarite=True)
    prepared_a = Card(5001, "Prepared A", spirit=3)
    prepared_b = Card(5002, "Prepared B")
    top = Card(5003, "Top")
    a = Wrestler("A", 0, 0, 0, kimarite, prepared_a, top)
    b = Wrestler("B", 0, 0, 0, Card(5004, "Tsukitaoshi", is_kimarite=True), prepared_b, top)

    fighter_a = FighterState(
        a,
        draw_pile=[Card(1, "One"), Card(2, "Two")],
        kimarite_zone=[kimarite],
    )
    fighter_a.left_grip = __import__("kimarite.models", fromlist=["GripState"]).GripState.GRIP
    fighter_a.right_grip = __import__("kimarite.models", fromlist=["GripState"]).GripState.GRIP
    bout = BoutState(fighter_a, FighterState(b, draw_pile=[Card(3, "Three")]))
    bout.position = 2
    comparison = compare_tachiai(a, b)

    from kimarite.turns import start_exchange_turn
    start_exchange_turn(bout, Side.A, comparison)

    assert bout.momentum == 1
    assert bout.winner is Side.A
    assert bout.win_method == "Yorikiri"
    assert bout.fighter_a.hand == []


def test_spirit_bonus_turn_is_taken_before_opponent_turn():
    a = make_wrestler("A", 0, 6, Stat.SPIRIT, Stat.POWER)
    b = make_wrestler("B", 0, 0, Stat.SPIRIT, Stat.POWER)
    bout = BoutState(
        FighterState(a, draw_pile=[Card(i, str(i)) for i in range(1, 7)]),
        FighterState(b, draw_pile=[Card(i, str(i)) for i in range(10, 16)]),
    )
    comparison = compare_tachiai(a, b)

    from kimarite.turns import end_exchange_turn, start_exchange_turn
    start_exchange_turn(bout, Side.A, comparison)
    next_side = end_exchange_turn(bout, Side.A)

    assert next_side is Side.A
    assert bout.fighter_a.bonus_turns_queued == 0


def test_multiple_satisfied_kimarite_default_to_earliest_played():
    from kimarite.models import GripState
    from kimarite.turns import check_kimarite_zone

    yorikiri = Card(6001, "Yorikiri", is_kimarite=True)
    oshidashi = Card(6002, "Oshidashi", is_kimarite=True)
    blank = Card(6003, "Blank")
    a = Wrestler("A", 5, 0, 0, yorikiri, blank, blank)
    b = Wrestler("B", 0, 0, 0, Card(6004, "Tsukitaoshi", is_kimarite=True), blank, blank)
    bout = BoutState(
        FighterState(a, kimarite_zone=[yorikiri, oshidashi], power=8),
        FighterState(b, power=0),
    )
    bout.fighter_a.left_grip = GripState.GRIP
    bout.fighter_a.right_grip = GripState.GRIP
    bout.momentum = 1
    bout.position = 2

    chosen = check_kimarite_zone(bout, Side.A)

    assert chosen is yorikiri
    assert bout.win_method == "Yorikiri"


def test_kimarite_chooser_can_override_earliest_for_reward_choice():
    from kimarite.models import GripState
    from kimarite.turns import check_kimarite_zone

    yorikiri = Card(6101, "Yorikiri", is_kimarite=True)
    oshidashi = Card(6102, "Oshidashi", is_kimarite=True)
    blank = Card(6103, "Blank")
    a = Wrestler("A", 5, 0, 0, yorikiri, blank, blank)
    b = Wrestler("B", 0, 0, 0, Card(6104, "Tsukitaoshi", is_kimarite=True), blank, blank)
    bout = BoutState(
        FighterState(a, kimarite_zone=[yorikiri, oshidashi], power=8),
        FighterState(b, power=0),
    )
    bout.fighter_a.left_grip = GripState.GRIP
    bout.fighter_a.right_grip = GripState.GRIP
    bout.momentum = 1
    bout.position = 2

    chosen = check_kimarite_zone(
        bout,
        Side.A,
        choose_kimarite=lambda state, side, cards: cards[1],
    )

    assert chosen is oshidashi
    assert bout.win_method == "Oshidashi"
