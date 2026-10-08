from kimarite.catalog import ORIGINAL_WRESTLERS
from kimarite.tachiai import compare_tachiai


def test_fujinokawa_vs_tochinoshin_prepared_totals_match_revised_builds():
    fujinokawa = ORIGINAL_WRESTLERS["Fujinokawa"].build()
    tochinoshin = ORIGINAL_WRESTLERS["Tochinoshin"].build()

    comparison = compare_tachiai(fujinokawa, tochinoshin)

    assert (
        comparison.wrestler_a.power,
        comparison.wrestler_a.technique,
        comparison.wrestler_a.spirit,
    ) == (4, 2, 8)
    assert (
        comparison.wrestler_b.power,
        comparison.wrestler_b.technique,
        comparison.wrestler_b.spirit,
    ) == (5, 7, 0)
