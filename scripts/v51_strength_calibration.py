"""225 entrants: 15 styles x difficulties -7..7; one bout per unordered pair."""
import argparse
import csv
import random
from collections import Counter
from pathlib import Path
from styles_test import roster, run_one

def entrants():
    return [(style, level) for style in roster() for level in range(-7, 8)]

def pairs(seed):
    result = [(i, j) for i in range(225) for j in range(i + 1, 225)]
    random.Random(seed).shuffle(result)
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=20261011)
    parser.add_argument("--max-turns", type=int, default=100)
    parser.add_argument("--output-dir", default="artifacts/v51_225_round_robin")
    args = parser.parse_args()
    players = entrants()
    matchups = pairs(args.seed)
    assert len(players) == 225 and len(matchups) == 25200
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    wins, bouts, errors = Counter(), Counter(), Counter()
    finishers_played, finishers_won = Counter(), Counter()
    from kimarite.catalog import STARTING_KIMARITE
    finisher_names = {c.name for c in STARTING_KIMARITE}
    with (output / "bouts.csv").open("w", newline="", encoding="utf8") as file:
        writer = csv.writer(file)
        writer.writerow(("a_style", "a_difficulty", "b_style", "b_difficulty", "seed", "winner", "method", "turns", "error"))
        for idx, (i, j) in enumerate(matchups):
            a, da = players[i]
            b, db = players[j]
            seed = args.seed + idx
            state, _, _, error = run_one(a, b, seed, args.max_turns, difficulty=da,
                                          opponent_difficulty=db, enable_stat_boosts=False)
            winner = state.winner.value if state.winner else ""
            writer.writerow((a[0], da, b[0], db, seed, winner, state.win_method or "", state.turn_number, error or ""))
            errors[error or "completed"] += 1
            # Include both pre-zoned starting finishers and later Kimarite plays.
            for fighter in (state.fighter_a, state.fighter_b):
                finishers_played[fighter.wrestler.starting_kimarite.name] += 1
            finishers_played.update(name for _, name in state.card_plays if name in finisher_names)
            if state.win_source == "kimarite" and state.win_method in finisher_names:
                finishers_won[state.win_method] += 1
            if error is None and winner:
                bouts[i] += 1
                bouts[j] += 1
                wins[i] += int(winner == "A")
                wins[j] += int(winner == "B")
            if (idx + 1) % 1000 == 0:
                print(f"{idx + 1:,}/25,200 bouts", flush=True)
    with (output / "entrants.csv").open("w", newline="", encoding="utf8") as file:
        writer = csv.writer(file)
        writer.writerow(("style", "difficulty", "bouts", "wins", "win_rate"))
        for i, (style, level) in enumerate(players):
            n = bouts[i]
            writer.writerow((style[0], level, n, wins[i], wins[i] / n if n else ""))
    with (output / "finisher_conversion.csv").open("w", newline="", encoding="utf8") as file:
        writer = csv.writer(file)
        writer.writerow(("kimarite", "entries_into_play", "successful_finishes", "finish_per_entry_ratio"))
        for name in sorted(finisher_names):
            n = finishers_played[name]
            writer.writerow((name, n, finishers_won[name], finishers_won[name] / n if n else ""))
    print(f"25,200 bouts: {dict(errors)}", flush=True)
    if errors != Counter({"completed": 25200}) or any(bouts[i] != 224 for i in range(225)):
        raise RuntimeError(f"Round robin incomplete: {dict(errors)}")

if __name__ == "__main__":
    main()
