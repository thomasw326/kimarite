"""V5.1 strength calibration: 225 style/difficulty builds vs a common baseline.

Every style at every difficulty (-7..7) faces every style at difficulty 0,
in both orientations. Allows fair cross-archetype win-rate comparisons.
"""
import argparse
import csv
from collections import Counter
from pathlib import Path

from styles_test import roster, run_one


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repetitions", type=int, default=3)
    p.add_argument("--max-turns", type=int, default=100)
    p.add_argument("--seed", type=int, default=20261011)
    p.add_argument("--output-dir", default="artifacts/v51_calibration")
    args = p.parse_args()
    assert args.repetitions > 0
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    configs = roster()
    assert len(configs) == 15
    counts = Counter()
    errors = Counter()
    total = 15 * 15 * 15 * 2 * args.repetitions
    with (out / "bouts.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(("challenger", "difficulty", "reference", "reference_difficulty", "repetition", "orientation", "seed", "winner", "win_method", "turns", "error"))
        completed = 0
        for d in range(-7, 8):
            for i, challenger in enumerate(configs):
                for j, reference in enumerate(configs):
                    for rep in range(args.repetitions):
                        for orientation in (0, 1):
                            seed = args.seed + (d + 7) * 1_000_000 + i * 20_000 + j * 1000 + rep * 2 + orientation
                            if orientation == 0:
                                bout, _, _, error = run_one(challenger, reference, seed, args.max_turns, difficulty=d, opponent_difficulty=0)
                                challenger_won = bout.winner is not None and bout.winner.value == "A"
                            else:
                                bout, _, _, error = run_one(reference, challenger, seed, args.max_turns, difficulty=0, opponent_difficulty=d)
                                challenger_won = bout.winner is not None and bout.winner.value == "B"
                            counts[(i, d, "bouts")] += int(bout.winner is not None and error is None)
                            counts[(i, d, "wins")] += int(challenger_won and error is None)
                            counts[(i, d, j, "bouts")] += int(bout.winner is not None and error is None)
                            counts[(i, d, j, "wins")] += int(challenger_won and error is None)
                            errors[error or "completed"] += 1
                            writer.writerow((challenger[0], d, reference[0], 0, rep, orientation, seed,
                                             bout.winner.value if bout.winner else "", bout.win_method or "", bout.turn_number, error or ""))
                            completed += 1
                            if completed % 1000 == 0:
                                print(f"{completed:,}/{total:,} bouts finished", flush=True)
    with (out / "style_difficulty.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(("style", "difficulty", "bouts", "wins", "win_rate"))
        for i, config in enumerate(configs):
            for d in range(-7, 8):
                n = counts[(i, d, "bouts")]
                wins = counts[(i, d, "wins")]
                w.writerow((config[0], d, n, wins, wins / n if n else ""))
    with (out / "opponent_breakdown.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(("style", "difficulty", "reference", "bouts", "wins", "win_rate"))
        for i, config in enumerate(configs):
            for d in range(-7, 8):
                for j, ref in enumerate(configs):
                    n = counts[(i, d, j, "bouts")]
                    wins = counts[(i, d, j, "wins")]
                    w.writerow((config[0], d, ref[0], n, wins, wins / n if n else ""))
    # Direct Mountain-vs-Speed Demon cross-difficulty grid, each side
    # facing the other at all 15 difficulty levels, in mirrored orientations.
    mountain = next(config for config in configs if config[0] == "Mountain")
    speed = next(config for config in configs if config[0] == "Speed Demon")
    with (out / "mountain_vs_speed_demon.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(("mountain_difficulty", "speed_demon_difficulty", "bouts", "mountain_wins", "mountain_win_rate", "errors"))
        for dm in range(-7, 8):
            for ds in range(-7, 8):
                n = wins = failures = 0
                for rep in range(args.repetitions):
                    for orientation in (0, 1):
                        seed = args.seed + 100_000_000 + (dm + 7) * 10000 + (ds + 7) * 100 + rep * 2 + orientation
                        if orientation == 0:
                            bout, _, _, error = run_one(mountain, speed, seed, args.max_turns, difficulty=dm, opponent_difficulty=ds)
                            mountain_win = bout.winner is not None and bout.winner.value == "A"
                        else:
                            bout, _, _, error = run_one(speed, mountain, seed, args.max_turns, difficulty=ds, opponent_difficulty=dm)
                            mountain_win = bout.winner is not None and bout.winner.value == "B"
                        if error is not None or bout.winner is None:
                            failures += 1
                        else:
                            n += 1
                            wins += int(mountain_win)
                w.writerow((dm, ds, n, wins, wins / n if n else "", failures))
                if failures:
                    errors["direct_comparison_failures"] += failures
    print(f"Completed {total:,} scheduled bouts. Outcomes: {dict(errors)}", flush=True)
    if any(k != "completed" for k in errors):
        raise RuntimeError(f"Some bouts failed or hit turn limit: {dict(errors)}")


if __name__ == "__main__":
    main()
