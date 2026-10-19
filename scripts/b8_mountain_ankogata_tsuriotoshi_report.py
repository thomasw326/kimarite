"""Aggregate 1000 Ankogata/Tsuriotoshi Mountain bouts versus four frozen B8 wrestlers."""
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
        assert m["bouts"] == m["completed"] == 200 and m["incomplete"] == 0, m
        assert m["stop"] - m["start"] == 25, m
        ranges.add((m["start"], m["stop"]))
        with (folder / "bouts.csv").open(newline="", encoding="utf-8") as f:
            bouts.extend(csv.DictReader(f))
        with (folder / "cards.csv").open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                key = (row["style"], row["opponent"], row["card"])
                for field, value in row.items():
                    if field not in ("style", "opponent", "card"):
                        cards[key][field] += int(value)
    assert ranges == {(i*25, (i+1)*25) for i in range(5)}, ranges
    assert len(bouts) == 1000
    assert all(r["completed"] == "True" and not r["error"] for r in bouts)
    assert all(r["winner_style"] for r in bouts)
    with (args.output / "all_bouts.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=bouts[0])
        w.writeheader()
        w.writerows(bouts)
    matchup = defaultdict(Counter)
    methods = Counter()
    mirrors = defaultdict(Counter)
    torinaoshi = Counter()
    for r in bouts:
        pair = tuple(sorted((r["style_a"], r["style_b"])))
        c = matchup[pair]
        c["bouts"] += 1
        c["torinaoshi"] += int(r["torinaoshi"])
        torinaoshi[pair] += int(r["torinaoshi"])
        c[r["winner_style"]] += 1
        c["seat_a_wins"] += int(r["seat_a_won"])
        if r["style_a"] == r["style_b"]:
            mirrors[r["style_a"]]["bouts"] += 1
            mirrors[r["style_a"]]["seat_a_wins"] += int(r["seat_a_won"])
        methods[(*pair, r["win_method"])] += 1
    assert len(matchup) == 4 and all("Mountain" in k and v["bouts"] == 250 for k, v in matchup.items())
    assert not mirrors
    summary = {
        "total_bouts": 1000, "cross_bouts": 1000, "mirror_bouts": 0,
        "matchups": [{"styles": list(k), **dict(v)} for k, v in sorted(matchup.items())],
        "torinaoshi_count": sum(torinaoshi.values()),
        "bouts_requiring_torinaoshi": sum(int(r["torinaoshi"]) > 0 for r in bouts),
        "mirror_seat_a_win_rates": {k: round(100 * v["seat_a_wins"] / v["bouts"], 3) for k, v in sorted(mirrors.items())},
    }
    summary["baseline"] = {"overall": 46.3, "per_opponent": {"Pressure Fighter": 58.4, "Fast Grappler": 40.0, "The Technician": 29.2, "Charger": 57.6}}
    summary["threshold_13"] = {"overall": 59.2, "per_opponent": {"Pressure Fighter": 71.6, "Fast Grappler": 52.4, "The Technician": 41.6, "Charger": 71.2}, "tsuriotoshi_finisher_wins": 323, "oshitaoshi_finisher_wins": 130}
    summary["mountain_wins"] = sum(v["Mountain"] for v in matchup.values())
    summary["mountain_win_pct"] = round(100 * summary["mountain_wins"] / 1000, 2)
    summary["per_opponent"] = {next(n for n in pair if n != "Mountain"): {"mountain_wins": v["Mountain"], "opponent_wins": 250-v["Mountain"], "mountain_win_pct": round(100*v["Mountain"]/250,2)} for pair,v in matchup.items()}
    summary["change_vs_baseline_pp"] = {name: round(v["mountain_win_pct"]-summary["baseline"]["per_opponent"][name],2) for name,v in summary["per_opponent"].items()}
    summary["overall_change_pp"] = round(summary["mountain_win_pct"]-summary["baseline"]["overall"],2)
    summary["change_vs_threshold_13_pp"] = {name: round(v["mountain_win_pct"]-summary["threshold_13"]["per_opponent"][name],2) for name,v in summary["per_opponent"].items()}
    summary["overall_change_vs_threshold_13_pp"] = round(summary["mountain_win_pct"]-summary["threshold_13"]["overall"],2)
    summary["tsuriotoshi_threshold"] = 15
    summary["baseline_15_griptrim"] = {"overall": 51.7, "per_opponent": {"Pressure Fighter": 62.0, "Fast Grappler": 46.0, "The Technician": 32.8, "Charger": 66.0}}
    summary["change_vs_baseline_15_griptrim_pp"] = {name: round(v["mountain_win_pct"]-summary["baseline_15_griptrim"]["per_opponent"][name], 2) for name,v in summary["per_opponent"].items()}
    summary["overall_change_vs_baseline_15_griptrim_pp"] = round(summary["mountain_win_pct"]-51.7,2)
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2))
    import os
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
            f.write(f"## Mountain with Ottsuke/Kannuki restored, Tsuriotoshi 15 — 1000 bouts\n\nMountain: {summary['mountain_wins']}/1000 ({summary['mountain_win_pct']}%)\n\n")
            for opponent, d in sorted(summary["per_opponent"].items()):
                f.write(f"- {opponent}: {d['mountain_wins']}/250 ({d['mountain_win_pct']}%)\n")
            f.write(f"\nVs prior 15-point deck: {summary['overall_change_vs_baseline_15_griptrim_pp']:+.1f} pp. Vs threshold 13: {summary['overall_change_vs_threshold_13_pp']:+.1f} pp. Vs original baseline: {summary['overall_change_pp']:+.1f} pp. Torinaoshi: {summary['torinaoshi_count']}\n")
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
    print(json.dumps({"total_bouts": 1000, "matchup_count": 4, "mirror_count": 0,
                      "incomplete": 0}, indent=2), flush=True)


if __name__ == "__main__":
    main()
