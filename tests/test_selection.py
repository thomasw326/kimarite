from kimarite.models import Card, FighterState, Stat, Wrestler
from kimarite.selection import ai_choose_from_look, ai_look_keep


def wrestler() -> Wrestler:
    blank = Card(100, "Blank")
    return Wrestler(
        "Selector",
        0,
        0,
        0,
        blank,
        blank,
        blank,
        primary=Stat.TECHNIQUE,
        secondary=Stat.SPIRIT,
    )


def test_ai_selection_uses_primary_secondary_then_reveal_order():
    cards = [
        Card(1, "A", technique=2, spirit=1),
        Card(2, "B", technique=3, spirit=0),
        Card(3, "C", technique=2, spirit=2),
        Card(4, "D", technique=2, spirit=2),
    ]

    chosen = ai_choose_from_look(cards, wrestler(), 3)

    assert [card.card_id for card in chosen] == [2, 3, 4]


def test_unchosen_looked_cards_go_to_bottom_in_reveal_order():
    cards = [
        Card(1, "A", technique=0),
        Card(2, "B", technique=3),
        Card(3, "C", technique=1),
        Card(4, "D", technique=2),
        Card(5, "E", technique=0),
    ]
    fighter = FighterState(wrestler(), draw_pile=list(cards))

    kept = ai_look_keep(fighter, look=4, keep=2)

    assert [card.card_id for card in kept] == [2, 4]
    assert [card.card_id for card in fighter.hand] == [2, 4]
    assert [card.card_id for card in fighter.draw_pile] == [5, 1, 3]


def test_look_keep_with_short_deck_keeps_all_available_cards():
    fighter = FighterState(
        wrestler(),
        draw_pile=[Card(99, "Only", technique=1)],
    )

    kept = ai_look_keep(fighter, look=4, keep=2)

    assert [card.card_id for card in kept] == [99]
    assert [card.card_id for card in fighter.hand] == [99]
    assert fighter.draw_pile == []
