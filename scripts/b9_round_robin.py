"""B9 15-wrestler round-robin using the exact 40-card lists checked into data/.
Run: python scripts/b9_round_robin.py --bouts 2000 --output-dir artifacts/b9
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

from kimarite.catalog import card_by_name
from kimarite.kimarite import KIMARITE_PREDICATES
from kimarite.models import BoutState, FighterState, Side, Stat, Wrestler
from kimarite.styles_v5 import STYLES
from kimarite.style_ai_v5 import play_style_turn
from kimarite.tachiai import compare_tachiai, first_exchange_side
from kimarite.tachiai_effects import resolve_prepared_tachiai
from kimarite.turns import apply_initial_power, end_exchange_turn, start_exchange_turn

DATA = Path(__file__).resolve().parent.parent / "data" / "b9_wrestler_decks.json"


def load_decks():
    decks = json.loads(DATA.read_text(encoding="utf-8"))["decks"]
    if len(decks) != 15:
        raise ValueError(f"Expected 15 wrestlers, got {len(decks)}")
    for name, record in decks.items():
        if len(record["cards"]) != 40:
            raise ValueError(f"{name} has {len(record['cards'])} rather than 40 cards")
        if any(card in {"Okuridashi", "Okuritaoshi"} for card in record["cards"]):
            raise ValueError(f"{name} includes generated-only Okuri cards")
        for card in record["cards"]:
            card_by_name(card)
    return decks


def make_fighter(name, entry, seed, ranking):
    rng = random.Random(seed)
    deck = [card_by_name(n) for n in entry["cards"]]
    kimarite = [c for c in deck if c.is_kimarite]
    ordinary = [c for c in deck if not c.is_kimarite]
    if not kimarite or len(ordinary) < 2:
        raise ValueError(f"Invalid B9 starting distribution for {name}")
    chosen_kimarite = kimarite.pop(rng.randrange(len(kimarite)))
    prepared = ordinary.pop(rng.randrange(len(ordinary)))
    top_card = ordinary.pop(rng.randrange(len(ordinary)))
    remainder = kimarite + ordinary
    rng.shuffle(remainder)
    profile = STYLES[name]
    order = [profile.primary, profile.secondary]
    order.extend(s.value for s in (Stat.POWER, Stat.TECHNIQUE, Stat.SPIRIT) if s.value not in order)
    # A style can give the same first and second priority; keep order distinct.
    order = list(dict.fromkeys(order))
    order.extend(s.value for s in (Stat.POWER, Stat.TECHNIQUE, Stat.SPIRIT) if s.value not in order)
    stats = entry["stats"]
    wrestler = Wrestler(
        name, stats["power"], stats["technique"], stats["spirit"],
        chosen_kimarite, prepared, top_card,
        primary=Stat(order[0]), secondary=Stat(order[1]), tertiary=Stat(order[2]),
        ranking=ranking,
    )
    fighter = FighterState(wrestler, draw_pile=[top_card, *remainder],
                           kimarite_zone=[chosen_kimarite])
    return fighter


def randomized_deck(entry, rng):
    """40-card unoptimized control: 5 distinct finishers and 35 Basics (max two copies)."""
    kimarite = [n for n in sorted(CARD_NAMES)
                if card_by_name(n).is_kimarite and n not in {"Okuridashi", "Okuritaoshi", "Utchari"}]
    basics = [n for n in sorted(CARD_NAMES) if not card_by_name(n).is_kimarite]
    cards = rng.sample(kimarite, 5) + rng.sample(basics * 2, 35)
    rng.shuffle(cards)
    return {"stats": entry["stats"], "cards": cards}


def run_one(name_a, name_b, decks, seed, max_turns, random_decks=False):
    if random_decks:
        randomized = random.Random(seed * 104729 + 19)
        decks = {name_a: randomized_deck(decks[name_a], randomized),
                 name_b: randomized_deck(decks[name_b], randomized)}
    a = make_fighter(name_a, decks[name_a], seed * 2, 1)
    b = make_fighter(name_b, decks[name_b], seed * 2 + 1, 2)
    state = BoutState(a, b)
    comparison = compare_tachiai(a.wrestler, b.wrestler)
    apply_initial_power(state, comparison)
    resolve_prepared_tachiai(state, comparison)
    if state.winner is None:
        state.active_side = first_exchange_side(comparison, a.wrestler, b.wrestler)
    turn = 0
    try:
        for turn in range(1, max_turns + 1):
            if state.winner is not None:
                break
            side = state.active_side
            start_exchange_turn(state, side, comparison)
            if state.winner is not None:
                break
            play_style_turn(state, side, comparison, name_a if side is Side.A else name_b)
            if state.winner is not None:
                break
            end_exchange_turn(state, side)
        error = "" if state.winner is not None else "turn_limit"
    except (ValueError, KeyError, RuntimeError, NotImplementedError) as exc:
        error = f"{type(exc).__name__}: {exc}"
    winner = name_a if state.winner is Side.A else name_b if state.winner is Side.B else ""
    return winner, state.win_method or "", turn, error, state, decks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bouts", type=int, default=2000)
    parser.add_argument("--max-turns", type=int, default=100)
    parser.add_argument("--seed", type=int, default=20261021)
    parser.add_argument("--output-dir", default="b9_artifacts")
    parser.add_argument("--fail-on-errors", action="store_true")
    parser.add_argument("--random-decks", action="store_true", help="Independently redraw 40 unoptimized cards for each wrestler-bout")
    args = parser.parse_args()
    decks = load_decks()
    if args.bouts < 1:
        parser.error("--bouts must be positive")
    names = list(decks)
    global CARD_NAMES
    CARD_NAMES = {card for entry in decks.values() for card in entry['cards']}
    pairs = list(combinations(names, 2))
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    wins, losses, errors, methods, played = Counter(), Counter(), Counter(), Counter(), Counter()
    methods_by_wrestler = {name: Counter() for name in names}
    matchup = {name: Counter() for name in names}
    opportunities = Counter()
    kimarite_available_bouts = Counter()
    kimarite_wins = Counter()
    # Restores per-card played/unplayed wrestler-bout win tracking from big_test.py.
    basic_card_outcomes = defaultdict(lambda: {"played_bouts": 0, "played_wins": 0,
                                                "unplayed_bouts": 0, "unplayed_wins": 0})
    with (output / "bouts.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["bout","wrestler_a","wrestler_b","winner","method","turns","error"])
        for idx in range(args.bouts):
            i = (idx // 2) % len(pairs)
            x, y = pairs[i]
            a, b = (x, y) if idx % 2 == 0 else (y, x)
            winner, method, turns, error, state, bout_decks = run_one(
                a, b, decks, args.seed + idx, args.max_turns, random_decks=args.random_decks
            )
            opportunities[a] += 1
            opportunities[b] += 1
            for side in (Side.A, Side.B):
                fighter = state.fighter(side)
                available = {fighter.wrestler.starting_kimarite.name}
                available.update(c.name for c in fighter.kimarite_zone)
                available.update(n for play_side, n in state.card_plays if play_side is side and n in KIMARITE_PREDICATES)
                for name in available:
                    kimarite_available_bouts[name] += 1
            if error:
                errors[error] += 1
            else:
                wins[winner] += 1
                loser = b if winner == a else a
                losses[loser] += 1
                methods[method] += 1
                if method in KIMARITE_PREDICATES:
                    kimarite_wins[method] += 1
                methods_by_wrestler[winner][method] += 1
                matchup[winner][loser] += 1
            played.update(name for _, name in state.card_plays)
            if not error:
                for side, wrestler_name in ((Side.A, a), (Side.B, b)):
                    # Only cards actually played during Exchange count as "played".
                    # All other cards in the wrestler's drafted 40-card pool are
                    # "unplayed"; duplicates count once per wrestler-bout.
                    played_names = {n for owner, n in state.card_plays if owner is side}
                    basic_names = {n for n in bout_decks[wrestler_name]["cards"]
                                   if n not in KIMARITE_PREDICATES}
                    for card_name in basic_names:
                        won = int(state.winner is side)
                        group = "played" if card_name in played_names else "unplayed"
                        for key in (("ALL", card_name), (wrestler_name, card_name)):
                            tally = basic_card_outcomes[key]
                            tally[group + "_bouts"] += 1
                            tally[group + "_wins"] += won
            writer.writerow([idx + 1, a, b, winner, method, turns, error])
            if (idx + 1) % 100 == 0:
                print(f"B9 completed {idx+1}/{args.bouts} bouts", flush=True)
    with (output / "basic_card_win_rates.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["wrestler", "card", "played_bouts", "played_wins",
                         "played_win_rate_percent", "unplayed_bouts", "unplayed_wins",
                         "unplayed_win_rate_percent", "difference_pp"])
        for (wrestler_name, card_name), tally in sorted(basic_card_outcomes.items()):
            pn, pw = tally["played_bouts"], tally["played_wins"]
            un, uw = tally["unplayed_bouts"], tally["unplayed_wins"]
            pr = round(100 * pw / pn, 2) if pn else None
            ur = round(100 * uw / un, 2) if un else None
            writer.writerow([wrestler_name, card_name, pn, pw, pr if pr is not None else "",
                             un, uw, ur if ur is not None else "",
                             round(pr - ur, 2) if pr is not None and ur is not None else ""])
    summary = {
        "requested_bouts": args.bouts,
        "completed_bouts": sum(wins.values()),
        "errors": dict(errors),
        "wrestlers": {name: {"wins": wins[name], "losses": losses[name],
            "win_rate": wins[name] / (wins[name] + losses[name])
            if wins[name] + losses[name] else 0} for name in names},
        "win_methods": dict(methods),
        "kimarite_win_rates": {name: {"wins": kimarite_wins[name], "available_wrestler_bouts": count, "win_rate_percent": round(100 * kimarite_wins[name] / count, 2)} for name, count in sorted(kimarite_available_bouts.items())},
        "cards_played": dict(played),
        "basic_card_win_rate_report": "basic_card_win_rates.csv",
        "winning_methods_by_wrestler": {name: dict(methods_by_wrestler[name]) for name in names},
        "head_to_head_wins": {name: dict(matchup[name]) for name in names},
        "scheduled_bouts_by_wrestler": dict(opportunities),
        "seed": args.seed,
        "random_decks": args.random_decks,
        "random_deck_design": "Five unique Kimarite plus 35 randomly sampled Basic cards (maximum two copies); all 40 newly selected per wrestler-bout",
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"completed": summary["completed_bouts"],
                      "errors": summary["errors"]}, indent=2))
    if args.fail_on_errors and (errors or sum(wins.values()) != args.bouts):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
