"""Combine any number of Big Test batch directories without averaging percentages."""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


def read_rows(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("batch_dirs", nargs="+", type=Path)
    parser.add_argument("--output-dir", default="combined_big_test")
    args = parser.parse_args()
    destination = Path(args.output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    seen_batches, seen_seeds = set(), set()
    totals = {}
    summaries = []

    for folder in args.batch_dirs:
        summary = json.loads((folder / "summary.json").read_text())
        batch_id = summary["batch_id"]
        if batch_id in seen_batches:
            raise ValueError(f"Duplicate batch ID: {batch_id}")
        seen_batches.add(batch_id)
        bouts = read_rows(folder / "bouts.csv")
        if len(bouts) != summary["planned_bouts"]:
            raise ValueError(f"Missing bout records for batch {batch_id}")
        for bout in bouts:
            if int(bout["batch_id"]) != batch_id:
                raise ValueError("Bout batch identity mismatch")
            seed = int(bout["seed"])
            if seed in seen_seeds:
                raise ValueError(f"Duplicate seed {seed}")
            seen_seeds.add(seed)
        summaries.append(summary)

        for filename, keys in (
            ("wrestlers.csv", ("wrestler", "power", "technique", "spirit",
                              "primary", "secondary", "tertiary")),
            ("wrestler_cohorts.csv", ("group", "value_1", "value_2", "value_3")),
            ("card_assignments.csv", ("role", "card")),
            ("cards.csv", ("card", "outcome", "priority_slot", "priority_stat")),
            ("win_conditions.csv", ("win_category",)),
            ("kimarite_finishes_by_origin.csv", ("kimarite", "origin")),
            ("card_play_by_origin.csv", ("card", "origin")),
            ("stat_advantages.csv", ("stat", "signed_advantage")),
        ):
            data = totals.setdefault(filename, defaultdict(Counter))
            for row in read_rows(folder / filename):
                key = tuple(row[k] for k in keys)
                if "bouts" in row:
                    data[key]["bouts"] += int(row["bouts"])
                if "bouts_played" in row:
                    data[key]["bouts"] += int(row["bouts_played"])
                if "finishes" in row:
                    data[key]["finishes"] += int(row["finishes"])
                if "wins" in row:
                    data[key]["wins"] += int(row["wins"])

    for filename, data in totals.items():
        if filename == "wrestlers.csv":
            header = ("wrestler", "power", "technique", "spirit",
                      "primary", "secondary", "tertiary")
        elif filename == "wrestler_cohorts.csv":
            header = ("group", "value_1", "value_2", "value_3")
        elif filename == "card_assignments.csv":
            header = ("role", "card")
        elif filename == "cards.csv":
            header = ("card", "outcome", "priority_slot", "priority_stat")
        elif filename == "kimarite_finishes_by_origin.csv":
            header = ("kimarite", "origin")
        elif filename == "card_play_by_origin.csv":
            header = ("card", "origin")
        elif filename == "stat_advantages.csv":
            header = ("stat", "signed_advantage")
        else:
            header = ("win_category",)
        with (destination / filename).open("w", newline="") as handle:
            writer = csv.writer(handle)
            if filename == "win_conditions.csv":
                writer.writerow((*header, "bouts"))
                for key, counts in sorted(data.items()):
                    writer.writerow((*key, counts["bouts"]))
            elif filename == "kimarite_finishes_by_origin.csv":
                writer.writerow((*header, "finishes"))
                for key, counts in sorted(data.items()):
                    writer.writerow((*key, counts["finishes"]))
            else:
                count_label = ("bouts_played" if filename == "card_play_by_origin.csv"
                               else "bouts")
                writer.writerow((*header, count_label, "wins", "win_rate"))
                for key, counts in sorted(data.items()):
                    n = counts["bouts"]
                    writer.writerow((*key, n, counts["wins"],
                                     counts["wins"] / n if n else ""))

    manifest = {
        "batch_ids": sorted(seen_batches),
        "bouts": len(seen_seeds),
        "completed": sum(s["completed"] for s in summaries),
        "source_seeds_unique": True,
        "source_summaries": summaries,
    }
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps({k: manifest[k] for k in ("batch_ids", "bouts", "completed")}, indent=2))


if __name__ == "__main__":
    main()
