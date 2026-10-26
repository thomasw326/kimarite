"""Multiple committed Oshi/Tsuki effects obey the established reveal rule."""
from kimarite.b11_tachiai_reveals import plan_reveals
from kimarite.catalog import card_by_name


def cs(*names):
    return [card_by_name(n) for n in names]


def test_single_oshi_reveals_family_and_stopper():
    result = plan_reveals(cs("Oshi"), cs("Oshi", "Shove", "Harite"))
    assert [c.name for c in result.revealed] == ["Oshi", "Shove"]
    assert [c.name for c in result.remaining] == ["Harite"]
    assert result.orbs == (2, 0, 1)


def test_each_committed_oshi_starts_a_chain_in_order():
    result = plan_reveals(
        cs("Oshi", "Oshi"), cs("Tsuki", "Shove", "Oshi", "Harite", "Salt Throw")
    )
    assert [c.name for c in result.revealed] == ["Tsuki", "Shove", "Oshi", "Harite"]
    assert [c.name for c in result.remaining] == ["Salt Throw"]
    assert result.orbs == (6, 0, 2)


def test_non_reveal_commit_does_not_consume_deck():
    pile = cs("Shove", "Harite")
    result = plan_reveals(cs("Shove", "Oshidashi"), pile)
    assert not result.revealed
    assert result.remaining == tuple(pile)
    assert result.orbs == (0, 0, 0)


def test_empty_pile_is_safe():
    assert plan_reveals(cs("Oshi"), []).orbs == (0, 0, 0)
