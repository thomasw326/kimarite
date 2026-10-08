from kimarite.ai import score_state
from kimarite.catalog import card_by_name
from kimarite.models import BoutState, Card, FighterState, GripState, Side, Wrestler
from kimarite.temporary import add_temporary


def wrestler(name: str) -> Wrestler:
    blank = Card(7000 + len(name), f"{name} Blank")
    return Wrestler(name, 0, 0, 0, blank, blank, blank)


def test_ai_scoring_does_not_consume_shiko_stomp():
    bout = BoutState(
        FighterState(wrestler("A")),
        FighterState(wrestler("B")),
    )
    bout.fighter_a.left_grip = GripState.GRIP

    add_temporary(bout, Side.A, card_by_name("Shiko Stomp"), phase="pre-bout")
    add_temporary(bout, Side.B, card_by_name("Kannuki"), phase="exchange")

    before = [x.card.name for x in bout.fighter_a.temporary_zone]

    score_state(bout, Side.A)

    after = [x.card.name for x in bout.fighter_a.temporary_zone]
    assert before == ["Shiko Stomp"]
    assert after == before
