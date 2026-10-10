import pytest
from kimarite.style_round_robin_v5 import run_round_robin


def test_zero_repetitions():
    with pytest.raises(ValueError):
        run_round_robin(repetitions=0)
