"""Tests for the balanced 108-wrestler matchup schedule."""
import importlib.util
from collections import Counter
from pathlib import Path


spec = importlib.util.spec_from_file_location(
    "big_test", Path(__file__).resolve().parents[1] / "scripts" / "big_test.py"
)
big_test = importlib.util.module_from_spec(spec)
spec.loader.exec_module(big_test)


def test_every_pair_appears_once_in_complete_round_robin():
    pairs = big_test.round_robin_pairs(108, 20261009)
    assert len(pairs) == 5778
    assert len({frozenset(p) for p in pairs}) == 5778
    counts = Counter(i for pair in pairs for i in pair)
    assert set(counts.values()) == {107}


def test_3000_pairs_have_nearly_equal_exposure():
    pairs = big_test.round_robin_pairs(108, 20261009)[:3000]
    counts = Counter(i for pair in pairs for i in pair)
    assert len(counts) == 108
    assert min(counts.values()) == 55
    assert max(counts.values()) == 56
    assert sum(counts.values()) == 6000
    assert pairs == big_test.round_robin_pairs(108, 20261009)[:3000]


def test_short_run_is_balanced_too():
    pairs = big_test.round_robin_pairs(108, 20261009)[:54]
    counts = Counter(i for pair in pairs for i in pair)
    assert len(counts) == 108
    assert set(counts.values()) == {1}
