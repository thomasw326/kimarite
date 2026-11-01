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


def test_equal_grip_removal_uses_attacker_seat():
    from kimarite.rules import reduce_grip
    for attacking, expected in ((Side.A, "left"), (Side.B, "right")):
        bout = BoutState(FighterState(wrestler("A")), FighterState(wrestler("B")))
        target = bout.opponent_side(attacking)
        victim = bout.fighter(target)
        victim.left_grip = GripState.GRIP
        victim.right_grip = GripState.GRIP
        reduce_grip(bout, target)
        assert (victim.left_grip is GripState.NONE) == (expected == "left")
        assert (victim.right_grip is GripState.NONE) == (expected == "right")


def test_ai_grip_tie_break_honours_finish_threat_before_seat():
    from kimarite.ai import _best_grip_to_reduce
    for attacking in (Side.A, Side.B):
        for threat, expected in (("Uwatenage", "left"), ("Shitatenage", "right")):
            bout = BoutState(FighterState(wrestler("A")), FighterState(wrestler("B")))
            target = bout.opponent(attacking)
            target.left_grip = GripState.DEEP
            target.right_grip = GripState.DEEP
            target.kimarite_zone = [card_by_name(threat)]
            assert _best_grip_to_reduce(bout, attacking) == expected
        bout = BoutState(FighterState(wrestler("A")), FighterState(wrestler("B")))
        target = bout.opponent(attacking)
        target.left_grip = GripState.DEEP
        target.right_grip = GripState.DEEP
        assert _best_grip_to_reduce(bout, attacking) == ("left" if attacking is Side.A else "right")
