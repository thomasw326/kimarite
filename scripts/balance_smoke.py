from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from kimarite.batch import run_round_robin, standings, summarize_series
from kimarite.catalog import PLAYTEST_WRESTLERS


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bouts-per-orientation", type=int, default=1)
    parser.add_argument("--output-dir", default="balance_artifacts")
    parser.add_argument("--max-turns", type=int, default=100)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    names = list(PLAYTEST_WRESTLERS)
    records = run_round_robin(
        names,
        bouts_per_orientation=args.bouts_per_orientation,
        max_turns=args.max_turns,
        seed_start=1,
    )
    table = standings(records)
    summary = summarize_series(records)

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
                record.unsupported_reason or "",
            ])

    incomplete = Counter(
        record.unsupported_reason or "unknown"
        for record in records
        if not record.completed
    )
    payload = {
        "wrestlers": names,
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
        "incomplete_reasons": dict(incomplete),
        "standings": [asdict(row) for row in table],
    }
    (output_dir / "summary.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
