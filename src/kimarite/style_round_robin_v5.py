"""Reproducible V5 15-style round robin (including CI baseline runs).

Usage: python -m kimarite.style_round_robin_v5 --repetitions 2
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from itertools import combinations

from .style_simulate_v5 import run_style_bout
from .style_builds_v5 import build_style
from .models import Side
from .styles_v5 import STYLES


def run_round_robin(*, repetitions: int = 1, seed: int = 20261009, max_turns: int = 100) -> dict:
    if repetitions < 1:
        raise ValueError("repetitions must be at least 1")
    styles = tuple(STYLES)
    wins = Counter()
    losses = Counter()
    finishes = Counter()
    unresolved = Counter()
    bouts = 0
    opening_finishes = 0
    first_side_wins = 0
    incomplete_by_style = Counter()
    pair_wins = Counter()
    finishes_by_winner = Counter()
    opening_losses = Counter()
    card_plays_by_style = Counter()
    turns_by_style = Counter()
    slot_outcomes = Counter()
    style_slot_outcomes = Counter()
    katasukashi_trigger_sources = Counter()
    headlong_choice_counts = Counter()
    headlong_choice_outcomes = Counter()
    for repeat in range(repetitions):
        for pair_index, (first, second) in enumerate(combinations(styles, 2)):
            # Use one common seed for both seat assignments in a matchup.
            # The styles still generate their own seeded decks by seat, so this
            # controls the base RNG seed; it does not make hands identical.
            pair_seed = seed + repeat * 10000 + pair_index
            for a, b in ((first, second), (second, first)):
                result = run_style_bout(
                    a, b, seed=pair_seed,
                    max_turns=max_turns,
                )
                bouts += 1
                # Rebuild each seeded participant for role attribution. Build inputs
                # exactly match run_style_bout, with ranking 1/2 and seed +1009.
                # These are observational win rates, not causal card effects.
                builds = (
                    build_style(a, seed=pair_seed, ranking=1),
                    build_style(b, seed=pair_seed + 1009, ranking=2),
                )
                for idx, build in enumerate(builds):
                    w = build.fighter.wrestler
                    role_cards = (
                        ("Starting Kimarite", (w.starting_kimarite,)),
                        ("Tachiai", (w.prepared_tachiai_card,)),
                        ("Top", (w.top_of_deck_card,)),
                        ("Opening Hand", tuple(
                            dict.fromkeys(result.state.first_exchange_hands.get(
                                Side.A if idx == 0 else Side.B, ()
                            ))
                        )),
                        ("Shuffled", tuple({
                            card.name: card for card in build.fighter.draw_pile[1:-1]
                        }.values())),
                    )
                    for role, cards in role_cards:
                        for c in cards:
                            slot_outcomes[(role, c.name, "appearances")] += 1
                            style_slot_outcomes[(w.name, role, c.name, "appearances")] += 1
                            if result.completed:
                                outcome = "wins" if result.state.winner.value == ("A" if idx == 0 else "B") else "losses"
                                slot_outcomes[(role, c.name, outcome)] += 1
                                style_slot_outcomes[(w.name, role, c.name, outcome)] += 1
                for deciding_side, phase, decision, sacrificed_name in result.state.headlong_decisions:
                    style_name = a if deciding_side is Side.A else b
                    headlong_choice_counts[(phase, decision)] += 1
                    headlong_choice_outcomes[(phase, decision, style_name, "wins" if result.state.winner is deciding_side else "losses")] += 1
                if result.completed and result.state.win_method == "Katasukashi":
                    for source in result.state.katasukashi_win_sources or ["unattributed"]:
                        katasukashi_trigger_sources[source] += 1
                for played_side, card_name in result.state.card_plays:
                    card_plays_by_style[(a if played_side.value == 'A' else b, card_name)] += 1
                turns_by_style[a] += result.turns
                turns_by_style[b] += result.turns
                if not result.completed:
                    unresolved[result.unsupported_reason or "incomplete"] += 1
                    incomplete_by_style[a] += 1
                    incomplete_by_style[b] += 1
                    continue
                if result.turns == 0:
                    opening_finishes += 1
                    opening_losses[b if result.state.winner.value == "A" else a] += 1
                if result.state.winner.value == "A":
                    first_side_wins += 1
                winner = a if result.state.winner.value == "A" else b
                loser = b if result.state.winner.value == "A" else a
                wins[winner] += 1
                losses[loser] += 1
                pair_wins[(winner, loser)] += 1
                finish = result.state.win_method or "unknown"
                if result.state.win_source == "ringout":
                    finish = ("Ringout with Grab" if finish == "Yorikiri"
                              else "Grabless Ringout" if finish == "Oshidashi"
                              else finish)
                finishes_by_winner[(winner, finish)] += 1
                finishes[finish] += 1
    return {
        "styles": len(styles), "planned_bouts": bouts,
        "completed": sum(wins.values()),
        "unresolved": dict(unresolved),
        "incomplete_by_style": dict(incomplete_by_style),
        "opening_finishes": opening_finishes,
        "first_side_wins": first_side_wins,
        "opening_losses_by_style": dict(opening_losses),
        "exchange_plays_by_style": {
            style: {card: count for (name, card), count in card_plays_by_style.items() if name == style}
            for style in styles
        },
        "average_bout_turns_by_style": {
            style: round(turns_by_style[style] / (2 * (len(styles) - 1) * repetitions), 2)
            for style in styles
        },
        "wins_by_finish_and_style": {
            style: {finish: count for (name, finish), count in finishes_by_winner.items() if name == style}
            for style in styles
        },
        "matchup_wins": {
            style: {opponent: pair_wins[(style, opponent)] for opponent in styles if opponent != style}
            for style in styles
        },
        "katasukashi_position_loss_triggers": dict(katasukashi_trigger_sources),
        "headlong_charge_ai_choices": {
            phase: {
                decision: {
                    "count": headlong_choice_counts[(phase, decision)],
                    "wins": sum(count for (p, d, style, result), count in headlong_choice_outcomes.items() if p == phase and d == decision and result == "wins"),
                    "losses": sum(count for (p, d, style, result), count in headlong_choice_outcomes.items() if p == phase and d == decision and result == "losses"),
                    "by_style": {
                        style: {
                            "wins": headlong_choice_outcomes[(phase, decision, style, "wins")],
                            "losses": headlong_choice_outcomes[(phase, decision, style, "losses")],
                        }
                        for style in styles
                        if headlong_choice_outcomes[(phase, decision, style, "wins")] + headlong_choice_outcomes[(phase, decision, style, "losses")]
                    },
                }
                for decision in ("sacrifice", "decline")
            }
            for phase in ("Tachiai", "Exchange")
        },
        "style_card_slot_outcomes": {
            style: {
                role: {
                    name: {
                        "appearances": style_slot_outcomes[(style, role, name, "appearances")],
                        "wins": style_slot_outcomes[(style, role, name, "wins")],
                        "losses": style_slot_outcomes[(style, role, name, "losses")],
                        "win_rate": round(
                            style_slot_outcomes[(style, role, name, "wins")] /
                            (style_slot_outcomes[(style, role, name, "wins")] +
                             style_slot_outcomes[(style, role, name, "losses")]), 4
                        ) if (style_slot_outcomes[(style, role, name, "wins")] +
                              style_slot_outcomes[(style, role, name, "losses")]) else None,
                    }
                    for name in sorted({
                        card_name for (style_name, slot, card_name, field) in style_slot_outcomes
                        if style_name == style and slot == role and field == "appearances"
                    })
                }
                for role in ("Starting Kimarite", "Tachiai", "Top", "Opening Hand", "Shuffled")
            }
            for style in styles
        },
        "style_card_placement_lift": {
            style: {
                role: {
                    name: {
                        "appearances": style_slot_outcomes[(style, role, name, "appearances")],
                        "wins": style_slot_outcomes[(style, role, name, "wins")],
                        "losses": style_slot_outcomes[(style, role, name, "losses")],
                        "win_rate": round(
                            style_slot_outcomes[(style, role, name, "wins")] /
                            (style_slot_outcomes[(style, role, name, "wins")] +
                             style_slot_outcomes[(style, role, name, "losses")]), 4
                        ) if (style_slot_outcomes[(style, role, name, "wins")] +
                              style_slot_outcomes[(style, role, name, "losses")]) else None,
                        "lift_vs_style_pp": round(
                            100 * (
                                style_slot_outcomes[(style, role, name, "wins")] /
                                (style_slot_outcomes[(style, role, name, "wins")] +
                                 style_slot_outcomes[(style, role, name, "losses")])
                                - wins[style] / (wins[style] + losses[style])
                            ), 2
                        ) if (style_slot_outcomes[(style, role, name, "wins")] +
                              style_slot_outcomes[(style, role, name, "losses")]
                              and wins[style] + losses[style]) else None,
                    }
                    for name in sorted({
                        card_name for (style_name, slot, card_name, field) in style_slot_outcomes
                        if style_name == style and slot == role and field == "appearances"
                    })
                }
                for role in ("Starting Kimarite", "Tachiai", "Top", "Opening Hand")
            }
            for style in styles
        },
        "card_slot_outcomes": {
            role: {
                name: {
                    "appearances": slot_outcomes[(role, name, "appearances")],
                    "wins": slot_outcomes[(role, name, "wins")],
                    "losses": slot_outcomes[(role, name, "losses")],
                    "win_rate": round(
                        slot_outcomes[(role, name, "wins")] /
                        (slot_outcomes[(role, name, "wins")] + slot_outcomes[(role, name, "losses")]), 4
                    ) if slot_outcomes[(role, name, "wins")] + slot_outcomes[(role, name, "losses")] else None,
                }
                for (category, name, field) in slot_outcomes if category == role
            }
            for role in ("Starting Kimarite", "Tachiai", "Top", "Opening Hand", "Shuffled")
        },
        "win_rates": {
            name: round(wins[name] / (wins[name] + losses[name]), 4)
            if wins[name] + losses[name] else None for name in styles
        },
        "finishes": dict(finishes),
        "repetitions": repetitions, "seed": seed,
        "seed_policy": "same base seed in both seat assignments per pairing",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--seed", type=int, default=20261009)
    parser.add_argument("--max-turns", type=int, default=100)
    args = parser.parse_args()
    print(json.dumps(run_round_robin(
        repetitions=args.repetitions, seed=args.seed, max_turns=args.max_turns,
    ), indent=2))


if __name__ == "__main__":
    main()
