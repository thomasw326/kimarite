"""Combine completed local R21 batch CSVs without selecting a winning variant.

Examples:
    python -m kimarite.r21_gauntlet_report artifacts/r21_batch_*.csv \
        --output-dir artifacts/r21_report

No simulations are run here. Duplicate fixtures across batches are rejected.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from math import sqrt
from pathlib import Path

from .r21_gauntlet import BoutRecord, generic_roster, load_arms, summarize_records


def _yes(raw: str) -> bool:
    if raw not in ("True", "False"):
        raise ValueError(f"Expected strict True/False CSV value, got {raw!r}")
    return raw == "True"


def wilson(successes: int, trials: int, *, z: float = 1.96) -> tuple[float | None, float | None]:
    if trials <= 0:
        return None, None
    p = successes / trials
    z2 = z * z
    denom = 1 + z2 / trials
    center = (p + z2 / (2 * trials)) / denom
    spread = z * sqrt((p * (1 - p) + z2 / (4 * trials)) / trials) / denom
    return round(max(0., center - spread), 6), round(min(1., center + spread), 6)


def read_bouts(paths: list[Path]) -> list[dict[str, object]]:
    if not paths:
        raise ValueError("At least one raw batch CSV is required")
    arms = {arm.arm_id: arm for arm in load_arms()}
    unique = set()
    output = []
    for path in paths:
        with path.open(newline="", encoding="utf-8") as file:
            for row in csv.DictReader(file):
                arm = arms.get(row["arm_id"])
                if arm is None or row["kimarite"] != arm.kimarite:
                    raise ValueError(f"Invalid arm/name in {path}: {row['arm_id']!r}")
                key = (row["arm_id"], row["placement"], row["fixture_id"],
                       row["subject_seat"], row["seed"])
                if key in unique:
                    raise ValueError(f"Duplicate R21 fixture across input batches: {key}")
                unique.add(key)
                for field in ("completed", "subject_won",
                              "finished_by_tested_kimarite",
                              "condition_attained", "tested_card_available"):
                    row[field] = _yes(row[field])
                for field in ("subject_index", "opponent_index", "seed", "turns"):
                    row[field] = int(row[field])
                if row["subject_seat"] not in ("A", "B"):
                    raise ValueError("Invalid A/B seat value")
                output.append(row)
    return output


def report(paths: list[Path]) -> dict[str, object]:
    rows = read_bouts(paths)
    records = [
        BoutRecord(
            arm_id=r["arm_id"], placement=r["placement"],
            subject_seat=r["subject_seat"], completed=r["completed"],
            subject_won=r["subject_won"],
            finished_by_tested_kimarite=r["finished_by_tested_kimarite"],
            condition_attained=r["condition_attained"],
            tested_card_available=r["tested_card_available"],
            error=r["error"],
        )
        for r in rows
    ]
    summary = summarize_records(records)
    for record in summary:
        win_lo, win_hi = wilson(record["wins"], record["completed"])
        finish_lo, finish_hi = wilson(record["kimarite_finishes"], record["completed"])
        record["win_rate_95ci_lower"] = win_lo
        record["win_rate_95ci_upper"] = win_hi
        record["kimarite_completion_95ci_lower"] = finish_lo
        record["kimarite_completion_95ci_upper"] = finish_hi

    roster = generic_roster()
    seats = defaultdict(Counter)
    profiles = defaultdict(Counter)
    causes = Counter()
    for r in rows:
        key = (r["arm_id"], r["placement"])
        if not r["completed"]:
            causes[(r["arm_id"], r["placement"], r["error"] or "incomplete")] += 1
        seat = seats[(*key, r["subject_seat"])]
        seat["scheduled"] += 1
        if r["completed"]:
            seat["completed"] += 1
            seat["wins"] += int(r["subject_won"])
            seat["finishes"] += int(r["finished_by_tested_kimarite"])

            profile = roster[r["subject_index"]]
            p = profiles[(*key, profile.stats, profile.priorities[0].value)]
            p["completed"] += 1
            p["wins"] += int(r["subject_won"])
            p["finishes"] += int(r["finished_by_tested_kimarite"])

    seat_rows = []
    for (arm, place, side), c in sorted(seats.items()):
        seat_rows.append({
            "arm_id": arm, "placement": place, "subject_seat": side,
            "scheduled": c["scheduled"], "completed": c["completed"],
            "wins": c["wins"], "finishes": c["finishes"],
            "win_rate": round(c["wins"]/c["completed"], 6) if c["completed"] else None,
        })
    profile_rows = []
    for (arm, place, stats, priority), c in sorted(profiles.items()):
        profile_rows.append({
            "arm_id": arm, "placement": place,
            "stats": "/".join(map(str, stats)), "primary": priority,
            "completed": c["completed"], "wins": c["wins"],
            "finishes": c["finishes"],
            "win_rate": round(c["wins"]/c["completed"], 6) if c["completed"] else None,
        })
    return {
        "about": {
            "experiment": "R21 generic-wrestler Kimarite gauntlet",
            "auto_selects_winning_variant": False,
            "seat_note": "Game is symmetric; A/B seat is a rare tie/first-mover diagnostic.",
            "inputs": [str(p) for p in paths],
            "raw_bouts": len(rows),
            "completed_bouts": sum(bool(r["completed"]) for r in rows),
        },
        "summary": summary,
        "seat_diagnostics": seat_rows,
        "profile_breakdown": profile_rows,
        "unresolved_reasons": [
            {"arm_id": a, "placement": b, "reason": reason, "count": n}
            for (a,b,reason),n in sorted(causes.items())
        ],
    }


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="+", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/r21_report"))
    args = parser.parse_args()
    result = report(args.input)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for key, file in (
        ("summary", "variant_placement_summary.csv"),
        ("seat_diagnostics", "seat_diagnostics.csv"),
        ("profile_breakdown", "generic_profile_breakdown.csv"),
        ("unresolved_reasons", "errors_and_incomplete.csv"),
    ):
        _write_csv(args.output_dir/file, result[key])
    with (args.output_dir/"report.json").open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(json.dumps({
        "summary_path": str(args.output_dir/"variant_placement_summary.csv"),
        "input_bouts": result["about"]["raw_bouts"],
        "completed_bouts": result["about"]["completed_bouts"],
        "group_count": len(result["summary"]),
        "seat_note": result["about"]["seat_note"],
    }, indent=2))


if __name__ == "__main__":
    main()
