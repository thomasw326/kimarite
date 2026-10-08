from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from kimarite.batch import run_round_robin, standings, summarize_series
from kimarite.catalog import ORIGINAL_WRESTLERS, PLAYTEST_WRESTLERS
from kimarite.exclusions import exclusions_for_difficulty



def advantage_diagnostics(records):
    bands = {
        "Power": {"1-2": [0, 0], "3-5": [0, 0], "6+": [0, 0]},
        "Technique": {"1-2": [0, 0], "3-5": [0, 0], "6+": [0, 0]},
        "Spirit": {"1-2": [0, 0], "3-5": [0, 0], "6+": [0, 0]},
    }

    for record in records:
        if not record.completed or record.winner is None:
            continue
        for label, value in (
            ("Power", record.power_advantage_a),
            ("Technique", record.technique_advantage_a),
            ("Spirit", record.spirit_advantage_a),
        ):
            if value == 0:
                continue
            magnitude = abs(value)
            band = "1-2" if magnitude <= 2 else "3-5" if magnitude <= 5 else "6+"
            advantaged = record.wrestler_a if value > 0 else record.wrestler_b
            bands[label][band][0] += 1
            if record.winner == advantaged:
                bands[label][band][1] += 1

    return {
        stat: {
            band: {
                "bouts": totals[0],
                "advantaged_wrestler_wins": totals[1],
                "conversion_rate": totals[1] / totals[0] if totals[0] else 0.0,
            }
            for band, totals in stat_bands.items()
        }
        for stat, stat_bands in bands.items()
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bouts-per-orientation", type=int, default=1)
    parser.add_argument("--output-dir", default="balance_artifacts")
    parser.add_argument("--max-turns", type=int, default=100)
    parser.add_argument(
        "--roster",
        choices=("all", "original"),
        default="all",
    )
    parser.add_argument("--difficulty", type=int, default=-7)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    names = (
        list(ORIGINAL_WRESTLERS)
        if args.roster == "original"
        else list(PLAYTEST_WRESTLERS)
    )

    if args.roster == "all" and args.difficulty != -7:
        raise ValueError(
            "Only the original 15 currently have authored exclusion priorities; "
            "use difficulty -7 for the full roster."
        )

    exclusions = {}
    if args.roster == "original":
        exclusions = {
            name: exclusions_for_difficulty(name, args.difficulty).excluded_ids
            for name in names
        }

    records = run_round_robin(
        names,
        bouts_per_orientation=args.bouts_per_orientation,
        exclusions_by_wrestler=exclusions,
        max_turns=args.max_turns,
        seed_start=1,
    )
    table = standings(records)
    summary = summarize_series(records)
    exchange_records = [record for record in records if record.turns > 0]
    exchange_table = standings(exchange_records) if exchange_records else []
    completed = [record for record in records if record.completed]
    phase_wins = Counter(
        "Tachiai" if record.turns == 0
        else "First Exchange Turn" if record.turns == 1
        else "Later Exchange"
        for record in completed
    )
    exchange_completed = [record for record in completed if record.turns > 0]
    first_actor_wins = sum(
        record.first_exchange_wrestler == record.winner
        for record in exchange_completed
        if record.first_exchange_wrestler is not None
    )

    with (output_dir / "standings.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "wrestler",
                "bouts",
                "completed_bouts",
                "wins",
                "losses",
                "win_rate",
            ],
        )
        writer.writeheader()
        for row in table:
            writer.writerow(asdict(row))

    with (output_dir / "bouts.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "wrestler_a",
            "wrestler_b",
            "seed_a",
            "seed_b",
            "completed",
            "winner",
            "win_method",
            "turns",
            "cards_played_a",
            "cards_played_b",
            "kimarite_removals_a",
            "kimarite_removals_b",
            "power_advantage_a",
            "technique_advantage_a",
            "spirit_advantage_a",
            "first_exchange_wrestler",
            "unsupported_reason",
        ])
        for record in records:
            writer.writerow([
                record.wrestler_a,
                record.wrestler_b,
                record.seed_a,
                record.seed_b,
                record.completed,
                record.winner or "",
                record.win_method or "",
                record.turns,
                "|".join(record.cards_played_a),
                "|".join(record.cards_played_b),
                "|".join(record.kimarite_removals_a),
                "|".join(record.kimarite_removals_b),
                record.power_advantage_a,
                record.technique_advantage_a,
                record.spirit_advantage_a,
                record.first_exchange_wrestler or "",
                record.unsupported_reason or "",
            ])

    incomplete = Counter(
        record.unsupported_reason or "unknown"
        for record in records
        if not record.completed
    )
    kimarite_removals = Counter(
        removed
        for record in records
        for removed in (
            *record.kimarite_removals_a,
            *record.kimarite_removals_b,
        )
    )

    payload = {
        "wrestlers": names,
        "roster": args.roster,
        "difficulty": args.difficulty,
        "bouts_per_orientation": args.bouts_per_orientation,
        "total_bouts": len(records),
        "completed_bouts": summary.completed_bouts,
        "completion_rate": (
            summary.completed_bouts / len(records) if records else 0.0
        ),
        "average_turns": summary.average_turns,
        "wins": summary.wins,
        "win_methods": summary.win_methods,
        "winning_card_uses": summary.winning_card_uses,
        "kimarite_removals": dict(kimarite_removals),
        "win_phase_counts": dict(phase_wins),
        "tachiai_forceout_rate": (
            phase_wins.get("Tachiai", 0) / len(completed)
            if completed else 0.0
        ),
        "first_actor_exchange_win_rate": (
            first_actor_wins / len(exchange_completed)
            if exchange_completed else 0.0
        ),
        "advantage_diagnostics": advantage_diagnostics(records),
        "exchange_only_advantage_diagnostics": advantage_diagnostics(
            exchange_records
        ),
        "incomplete_reasons": dict(incomplete),
        "standings": [asdict(row) for row in table],
        "exchange_only_standings": [asdict(row) for row in exchange_table],
    }
    (output_dir / "summary.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
