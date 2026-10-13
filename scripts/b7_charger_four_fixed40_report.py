"""Aggregate five verified 24k-shard B7 fifteen-archetype runs."""
import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    folders = sorted(m.parent for m in args.input.rglob("manifest.json"))
    assert len(folders) == 5, folders
    ranges, bouts = set(), []
    cards = defaultdict(Counter)
    for folder in folders:
        m = json.loads((folder / "manifest.json").read_text())
        assert m["bouts"] == m["completed"] == 2000 and m["incomplete"] == 0, m
        assert m["stop"] - m["start"] == 100, m
        ranges.add((m["start"], m["stop"]))
        with (folder / "bouts.csv").open(newline="", encoding="utf-8") as f:
            bouts.extend(csv.DictReader(f))
        with (folder / "cards.csv").open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                key = (row["style"], row["opponent"], row["card"])
                for field, value in row.items():
                    if field not in ("style", "opponent", "card"):
                        cards[key][field] += int(value)
    assert ranges == {(i, i + 100) for i in range(0, 500, 100)}, ranges
    assert len(bouts) == 10000
    assert all(r["completed"] == "True" and not r["error"] for r in bouts)
    with (args.output / "all_bouts.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=bouts[0])
        w.writeheader()
        w.writerows(bouts)
    matchup = defaultdict(Counter)
    methods = Counter()
    mirrors = defaultdict(Counter)
    for r in bouts:
        pair = tuple(sorted((r["style_a"], r["style_b"])))
        c = matchup[pair]
        c["bouts"] += 1
        c[r["winner_style"]] += 1
        c["seat_a_wins"] += int(r["seat_a_won"])
        if r["style_a"] == r["style_b"]:
            mirrors[r["style_a"]]["bouts"] += 1
            mirrors[r["style_a"]]["seat_a_wins"] += int(r["seat_a_won"])
        methods[(*pair, r["win_method"])] += 1
    assert len(matchup) == 10 and all(v["bouts"] == 1000 for v in matchup.values())
    assert len(mirrors) == 4 and all(v["bouts"] == 1000 for v in mirrors.values())
    summary = {
        "total_bouts": 10000, "cross_bouts": 6000, "mirror_bouts": 4000,
        "matchups": [{"styles": list(k), **dict(v)} for k, v in sorted(matchup.items())],
        "mirror_seat_a_win_rates": {k: round(100 * v["seat_a_wins"] / v["bouts"], 3) for k, v in sorted(mirrors.items())},
    }
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2))
    with (args.output / "win_methods.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(("style_1", "style_2", "method", "wins"))
        for key, n in sorted(methods.items()):
            w.writerow((*key, n))
    columns = ("deck_bouts", "deck_copies", "deck_wins", "played_bouts", "played_uses",
               "played_wins", "starting_bouts", "starting_wins", "prepared_bouts",
               "prepared_wins", "finisher_wins")
    with (args.output / "card_data.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(("style", "opponent", "card", *columns, "deck_win_pct", "played_win_pct"))
        for key, c in sorted(cards.items()):
            w.writerow((*key, *(c[col] for col in columns),
                round(100*c["deck_wins"]/c["deck_bouts"], 3) if c["deck_bouts"] else "",
                round(100*c["played_wins"]/c["played_bouts"], 3) if c["played_bouts"] else ""))
    print(json.dumps({"total_bouts": 10000, "matchup_count": 10, "mirror_count": 4,
                      "incomplete": 0}, indent=2), flush=True)


if __name__ == "__main__":
    main()
