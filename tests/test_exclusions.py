from kimarite.exclusions import exclusions_for_difficulty


def test_fujinokawa_difficulty_zero_matches_known_manual_exclusions():
    result = exclusions_for_difficulty("Fujinokawa", 0)

    assert result.target == 7
    assert result.excluded_ids == frozenset({7, 14, 15, 16, 29, 35, 43})


def test_tochinoshin_difficulty_zero_follows_written_priority():
    result = exclusions_for_difficulty("Tochinoshin", 0)

    assert result.target == 7
    # Written rule: Spirit-sensitive cards first, then non-Grip/non-Push
    # cards with the fewest combined Technique + Power.
    assert result.excluded_ids == frozenset({18, 19, 21, 28, 29, 31, 40})


def test_minus_seven_has_no_exclusions():
    result = exclusions_for_difficulty("Fujinokawa", -7)

    assert result.target == 0
    assert result.excluded_ids == frozenset()
