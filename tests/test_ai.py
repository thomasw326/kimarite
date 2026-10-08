from kimarite.ai import candidate_plays, next_turn_kimarite_state, score_state
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


def test_ottsuke_generates_distinct_grip_and_card_removal_candidates():
    from kimarite.catalog import card_by_name
    from kimarite.tachiai import compare_tachiai

    ottsuke = card_by_name("Ottsuke")
    tsuridashi = card_by_name("Tsuridashi", prefer_starting_kimarite=True)
    a = wrestler("A")
    b = wrestler("B")
    bout = BoutState(
        FighterState(a, hand=[ottsuke]),
        FighterState(b, kimarite_zone=[tsuridashi]),
    )
    bout.fighter_b.right_grip = GripState.GRIP
    comparison = compare_tachiai(a, b)

    plays = candidate_plays(bout, Side.A, comparison)
    modes = {
        (play.context.choices or {}).get("mode")
        for play in plays
        if play.card.name == "Ottsuke"
    }

    assert "reduce_grip" in modes
    assert "remove_card" in modes


def test_next_turn_threat_state_clears_transient_kimarite_flags():
    a = wrestler("A")
    b = wrestler("B")
    bout = BoutState(
        FighterState(a),
        FighterState(b),
    )
    bout.fighter_b.cards_played_this_turn = 4
    bout.fighter_b.lost_position_this_turn = True
    bout.fighter_b.opponent_grip_reduced_this_turn = True

    future = next_turn_kimarite_state(bout, Side.B)

    assert future.fighter_b.cards_played_this_turn == 0
    assert future.fighter_b.lost_position_this_turn is False
    assert future.fighter_b.opponent_grip_reduced_this_turn is False
    assert bout.fighter_b.cards_played_this_turn == 4
