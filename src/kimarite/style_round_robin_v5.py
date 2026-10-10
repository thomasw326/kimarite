"""Local-only V5 15-style round robin; no scheduled GitHub action.

Usage: python -m kimarite.style_round_robin_v5 --repetitions 2
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from itertools import combinations

from .style_simulate_v5 import run_style_bout
from .styles_v5 import STYLES


def run_round_robin(*, repetitions: int = 1, seed: int = 20261009, max_turns: int = 100) -> dict:
    if repetitions < 1:
        raise ValueError("repetitions must be at least 1")
    styles = tuple(STYLES)
    wins = Counter()
    losses = Counter()
    finishes = Counter()
    unresolved = Counter()
    bouts = 0
    opening_finishes = 0
    first_side_wins = 0
    incomplete_by_style = Counter()
    for repeat in range(repetitions):
        for pair_index, (first, second) in enumerate(combinations(styles, 2)):
            for leg, (a, b) in enumerate(((first, second), (second, first))):
                result = run_style_bout(
                    a, b, seed=seed + repeat * 10000 + pair_index * 2 + leg,
                    max_turns=max_turns,
                )
                bouts += 1
                if not result.completed:
                    unresolved[result.unsupported_reason or "incomplete"] += 1
                    incomplete_by_style[a] += 1
                    incomplete_by_style[b] += 1
                    continue
                if result.turns == 0:
                    opening_finishes += 1
                if result.state.winner.value == "A":
                    first_side_wins += 1
                winner = a if result.state.winner.value == "A" else b
                loser = b if result.state.winner.value == "A" else a
                wins[winner] += 1
                losses[loser] += 1
                finishes[result.state.win_method or "unknown"] += 1
    return {
        "styles": len(styles), "planned_bouts": bouts,
        "completed": sum(wins.values()),
        "unresolved": dict(unresolved),
        "incomplete_by_style": dict(incomplete_by_style),
        "opening_finishes": opening_finishes,
        "first_side_wins": first_side_wins,
        "win_rates": {
            name: round(wins[name] / (wins[name] + losses[name]), 4)
            if wins[name] + losses[name] else None for name in styles
        },
        "finishes": dict(finishes),
        "repetitions": repetitions, "seed": seed,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--seed", type=int, default=20261009)
    parser.add_argument("--max-turns", type=int, default=100)
    args = parser.parse_args()
    print(json.dumps(run_round_robin(
        repetitions=args.repetitions, seed=args.seed, max_turns=args.max_turns,
    ), indent=2))


if __name__ == "__main__":
    main()
