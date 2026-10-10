"""Targeted V5 Kimarite audit with explicit per-role denominators.

Run: python -m kimarite.kimarite_audit_v5 --repetitions 20 --max-turns 30 --output artifacts/kimarite-audit.json
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from itertools import combinations
from pathlib import Path

from .catalog import CARD_POOL
from .models import Side
from .style_builds_v5 import build_style
from .style_simulate_v5 import run_style_bout
from .styles_v5 import STYLES


def audit(*, repetitions: int = 20, seed: int = 20261010, max_turns: int = 30,
          disable_kimarite_exchange_effects: bool = False) -> dict:
    if repetitions < 1:
        raise ValueError("repetitions must be positive")
    kimarite_names = sorted({c.name for c in CARD_POOL if c.is_kimarite})
    counts = Counter()
    finishes = Counter()
    incomplete = Counter()
    bouts = 0

    for rep in range(repetitions):
        for pair_index, (first, second) in enumerate(combinations(STYLES, 2)):
            pair_seed = seed + rep * 10000 + pair_index
            for a, b in ((first, second), (second, first)):
                result = run_style_bout(a, b, seed=pair_seed, max_turns=max_turns,
                                        disable_kimarite_exchange_effects=disable_kimarite_exchange_effects)
                bouts += 1
                state = result.state
                if not result.completed or state.winner is None:
                    incomplete[result.unsupported_reason or "unknown"] += 1
                    continue

                for side, style, deck_seed in ((Side.A, a, pair_seed), (Side.B, b, pair_seed + 1009)):
                    build = build_style(style, seed=deck_seed, ranking=1 if side is Side.A else 2)
                    start = build.fighter.wrestler.starting_kimarite.name
                    deck_names = {card.name for card in build.fighter.draw_pile if card.is_kimarite}
                    deck_names.add(start)
                    won = state.winner is side
                    in_zone = {card.name for card in state.fighter(side).kimarite_zone}
                    for name in deck_names:
                        counts[name, "featured"] += 1
                        counts[name, "featured_wins"] += int(won)
                        if name in in_zone:
                            counts[name, "final_zone"] += 1
                            counts[name, "final_zone_wins"] += int(won)
                    counts[start, "starting"] += 1
                    counts[start, "starting_wins"] += int(won)

                # Only a genuine Kimarite predicate victory is credited as a
                # trigger. Generic ringouts sharing a Kimarite name do not count.
                if state.winning_kimarite_card_id is not None:
                    match = next((card.name for card in CARD_POOL
                                  if card.card_id == state.winning_kimarite_card_id), None)
                    if match in kimarite_names:
                        counts[match, "trigger_wins"] += 1
                        winner_start = state.fighter(state.winner).wrestler.starting_kimarite.name
                        if winner_start == match:
                            counts[match, "starting_trigger_wins"] += 1
                        else:
                            counts[match, "nonstarting_trigger_wins"] += 1
                finishes[state.win_method or "unknown"] += 1

    def rate(numerator: int, denominator: int):
        return round(numerator / denominator, 4) if denominator else None

    report = []
    for name in kimarite_names:
        get = lambda metric: counts[name, metric]
        record = {"kimarite": name}
        for key in ("featured", "featured_wins", "starting", "starting_wins",
                    "final_zone", "final_zone_wins", "trigger_wins",
                    "starting_trigger_wins", "nonstarting_trigger_wins"):
            record[key] = get(key)
        record["overall_win_rate"] = rate(get("featured_wins"), get("featured"))
        record["starting_win_rate"] = rate(get("starting_wins"), get("starting"))
        record["trigger_per_feature_rate"] = rate(get("trigger_wins"), get("featured"))
        record["trigger_per_start_rate"] = rate(get("starting_trigger_wins"), get("starting"))
        record["final_zone_win_rate"] = rate(get("final_zone_wins"), get("final_zone"))
        record["shuffled"] = get("featured") - get("starting")
        record["shuffled_wins"] = get("featured_wins") - get("starting_wins")
        record["shuffled_win_rate"] = rate(record["shuffled_wins"], record["shuffled"])
        record["shuffled_trigger_wins"] = get("nonstarting_trigger_wins")
        record["shuffled_trigger_rate"] = rate(record["shuffled_trigger_wins"], record["shuffled"])
        record["nonstarting_trigger_per_feature_rate"] = record["shuffled_trigger_rate"]
        report.append(record)
    return {"planned_bouts": bouts, "completed": bouts - sum(incomplete.values()),
            "incomplete": dict(incomplete), "repetitions": repetitions,
            "seed": seed, "max_turns": max_turns,
            "disable_kimarite_exchange_effects": disable_kimarite_exchange_effects,
            "kimarite": report,
            "finishes": dict(finishes),
            "notes": ["Featured means included in the starter or shuffled deck at setup.",
                      "Final-zone presence is a snapshot at bout end, not ever-in-play.",
                      "Win-trigger attribution uses winning_kimarite_card_id, not win_method alone.",
                      "Rates are observational; style-specific starter distributions may vary."]}


def main() -> None:
    parser = argparse.ArgumentParser(description="Targeted V5 Kimarite denominators and triggers")
    parser.add_argument("--repetitions", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20261010)
    parser.add_argument("--max-turns", type=int, default=30)
    parser.add_argument("--disable-kimarite-exchange-effects", action="store_true")
    parser.add_argument("--output", default="artifacts/kimarite-audit-v5.json")
    args = parser.parse_args()
    result = audit(repetitions=args.repetitions, seed=args.seed, max_turns=args.max_turns,
                   disable_kimarite_exchange_effects=args.disable_kimarite_exchange_effects)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Recorded {result['completed']}/{result['planned_bouts']} completed bouts in {output}")


if __name__ == "__main__":
    main()
