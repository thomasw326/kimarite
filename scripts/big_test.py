"""108-config randomized Big Test. Run with python scripts/big_test.py."""
from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter, defaultdict
from itertools import combinations, permutations
from pathlib import Path

from kimarite.catalog import CARD_POOL, STARTING_KIMARITE
from kimarite.models import BoutState, FighterState, Side, Stat, Wrestler
from kimarite.personality_ai import play_personality_turn
from kimarite.tachiai import compare_tachiai, first_exchange_side
from kimarite.tachiai_effects import resolve_prepared_tachiai
from kimarite.turns import apply_initial_power, end_exchange_turn, start_exchange_turn

# Read directly from the Stats tab on October 8, 2026; Power, Technique, Spirit.
STAT_BUILDS = (
    (4, 1, 0), (4, 0, 1), (3, 2, 0), (3, 0, 2),
    (3, 1, 1), (2, 2, 1), (2, 1, 2), (1, 4, 0),
    (0, 4, 1), (2, 3, 0), (0, 3, 2), (1, 3, 1),
    (1, 2, 2), (1, 0, 4), (0, 1, 4), (2, 0, 3),
    (0, 2, 3), (1, 1, 3),
)
ORDERS = tuple(permutations(Stat))


def roster():
    return [
        (f"S{index:02d}-{''.join(x.value[0] for x in order)}", stats, order)
        for index, stats in enumerate(STAT_BUILDS, 1)
        for order in ORDERS
    ]


def make_fighter(config, rng, ranking):
    name, stats, order = config
    kimarite = rng.choice(STARTING_KIMARITE)
    # Card assignment and shuffle are deliberately agnostic to wrestler statistics.
    pool = [card for card in CARD_POOL if card.name != kimarite.name]
    tachiai = rng.choice(pool)
    pool = [card for card in pool if card.card_id != tachiai.card_id]
    top_card = rng.choice(pool)
    pool = [card for card in pool if card.card_id != top_card.card_id]
    rng.shuffle(pool)
    wrestler = Wrestler(name, *stats, kimarite, tachiai, top_card,
                        primary=order[0], secondary=order[1], tertiary=order[2],
                        ranking=ranking)
    return FighterState(wrestler, draw_pile=[top_card, *pool],
                        kimarite_zone=[kimarite])


def run_one(a, b, seed, max_turns):
    rng = random.Random(seed)
    state = BoutState(make_fighter(a, rng, 1), make_fighter(b, rng, 2))
    comparison = compare_tachiai(state.fighter_a.wrestler, state.fighter_b.wrestler)
    apply_initial_power(state, comparison)
    resolve_prepared_tachiai(state, comparison)
    available = {Side.A: set(), Side.B: set()}
    played = {Side.A: set(), Side.B: set()}
    if state.winner is None:
        state.active_side = first_exchange_side(
            comparison, state.fighter_a.wrestler, state.fighter_b.wrestler
        )
    try:
        for _ in range(max_turns):
            if state.winner is not None:
                break
            side = state.active_side
            start_exchange_turn(state, side, comparison)
            if state.winner is not None:
                break
            available[side].update(card.name for card in state.fighter(side).hand)
            before = len(state.card_plays)
            play_personality_turn(state, side, comparison)
            played[side].update(
                name for owner, name in state.card_plays[before:] if owner is side
            )
            if state.winner is not None:
                break
            end_exchange_turn(state, side)
        error = None if state.winner is not None else "turn limit"
    except (ValueError, KeyError, NotImplementedError, RuntimeError) as exc:
        error = type(exc).__name__ + ": " + str(exc)
    return state, available, played, error


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repetitions", type=int, default=1,
                        help="Mirrored bouts per distinct pairing, per repetition")
    parser.add_argument("--max-turns", type=int, default=100)
    parser.add_argument("--output-dir", default="big_test_artifacts")
    parser.add_argument("--seed", type=int, default=20261008)
    args = parser.parse_args()
    if args.repetitions < 1:
        parser.error("--repetitions must be >= 1")
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    configs = roster()
    assert len(configs) == 108
    bouts = Counter()
    wins = Counter()
    cards = defaultdict(lambda: Counter())
    errors = Counter()

    with (output / "bouts.csv").open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(("a", "b", "seed", "winner", "method", "turns", "error"))
        for repeat in range(args.repetitions):
            for pair_idx, (i, j) in enumerate(combinations(range(108), 2)):
                for orientation, (left, right) in enumerate(((i, j), (j, i))):
                    seed = args.seed + repeat * 20000 + pair_idx * 2 + orientation
                    a, b = configs[left], configs[right]
                    state, available, played, error = run_one(a, b, seed, args.max_turns)
                    errors[error or "completed"] += 1
                    writer.writerow((a[0], b[0], seed,
                                     state.fighter(state.winner).wrestler.name
                                     if state.winner is not None else "",
                                     state.win_method or "", state.turn_number,
                                     error or ""))
                    if state.winner is None:
                        continue
                    for side, config in ((Side.A, a), (Side.B, b)):
                        name, _, priority = config
                        won = state.winner is side
                        bouts[name] += 1
                        wins[name] += int(won)
                        # Cards may be in hand multiple turns: count each card
                        # once per wrestler-bout, separating played from unplayed.
                        for card in available[side]:
                            kind = "played" if card in played[side] else "hand_unplayed"
                            for slot, stat in enumerate(priority, start=1):
                                key = (card, kind, slot, stat.value)
                                cards[key]["bouts"] += 1
                                cards[key]["wins"] += int(won)

    with (output / "wrestlers.csv").open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(("wrestler", "power", "technique", "spirit",
                         "primary", "secondary", "tertiary", "bouts", "wins", "win_rate"))
        for name, stats, priority in configs:
            n = bouts[name]
            writer.writerow((name, *stats, *(p.value for p in priority),
                             n, wins[name], wins[name] / n if n else ""))
    with (output / "cards.csv").open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(("card", "outcome", "priority_slot", "priority_stat",
                         "bouts", "wins", "win_rate"))
        for key, tally in sorted(cards.items(), key=lambda x: x[0][:3]):
            n = tally["bouts"]
            writer.writerow((*key, n, tally["wins"], tally["wins"] / n if n else ""))
    summary = {
        "configs": len(configs),
        "planned_bouts": args.repetitions * 108 * 107,
        "completed": errors["completed"],
        "errors": dict(errors),
        "repetitions": args.repetitions,
        "seed": args.seed,
        "max_turns": args.max_turns,
        "notes": "Per-card hand exposure counts distinct card names per wrestler-bout; played counts if played at least once. Priority slot describes wrestler AI preference, not card order. Excludes incomplete bouts from win rates.",
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
