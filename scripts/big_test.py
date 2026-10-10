"""108-config randomized Big Test. Run with python scripts/big_test.py."""
from __future__ import annotations

import argparse
import csv
import json
import random
import time
from collections import Counter, defaultdict
from itertools import permutations
from pathlib import Path

from kimarite.catalog import CARD_POOL, STARTING_KIMARITE
from kimarite.models import BoutState, FighterState, Side, Stat, Wrestler
from kimarite.personality_ai import play_personality_turn
from kimarite.tachiai import compare_tachiai, first_exchange_side
from kimarite.tachiai_effects import resolve_prepared_tachiai
from kimarite.turns import apply_initial_power, end_exchange_turn, start_exchange_turn

# Read directly from the Stats tab on October 8, 2026; Power, Technique, Spirit.
STAT_BUILDS = (
    (4, 1, 0), (4, 0, 1), (3, 2, 0), (3, 0, 2),
    (3, 1, 1), (2, 2, 1), (2, 1, 2), (1, 4, 0),
    (0, 4, 1), (2, 3, 0), (0, 3, 2), (1, 3, 1),
    (1, 2, 2), (1, 0, 4), (0, 1, 4), (2, 0, 3),
    (0, 2, 3), (1, 1, 3),
)
ORDERS = tuple(permutations(Stat))



def roster():
    return [
        (f"S{index:02d}-{''.join(x.value[0] for x in order)}", stats, order)
        for index, stats in enumerate(STAT_BUILDS, 1)
        for order in ORDERS
    ]


def make_fighter(config, rng, ranking):
    name, stats, order = config
    kimarite = rng.choice(STARTING_KIMARITE)
    # All names are eligible for each role, subject to the three assigned
    # card names being distinct. Exclude all copies from the remainder.
    tachiai = rng.choice([c for c in CARD_POOL if c.name != kimarite.name])
    top_card = rng.choice([
        c for c in CARD_POOL if c.name not in {kimarite.name, tachiai.name}
    ])
    reserved = {kimarite.name, tachiai.name, top_card.name}
    pool = [card for card in CARD_POOL if card.name not in reserved]
    rng.shuffle(pool)
    wrestler = Wrestler(name, *stats, kimarite, tachiai, top_card,
                        primary=order[0], secondary=order[1], tertiary=order[2],
                        ranking=ranking)
    return FighterState(wrestler, draw_pile=[top_card, *pool],
                        kimarite_zone=[kimarite])


def card_origin(wrestler, card_id):
    if card_id == wrestler.starting_kimarite.card_id:
        return "starting_kimarite"
    if card_id == wrestler.prepared_tachiai_card.card_id:
        return "prepared_tachiai"
    if card_id == wrestler.top_of_deck_card.card_id:
        return "top_of_deck"
    return "shuffled_remainder"


def run_one(a, b, seed, max_turns, *, neutral_opening_position=False):
    rng = random.Random(seed)
    state = BoutState(make_fighter(a, rng, 1), make_fighter(b, rng, 2))
    comparison = compare_tachiai(state.fighter_a.wrestler, state.fighter_b.wrestler)
    apply_initial_power(state, comparison)
    resolve_prepared_tachiai(state, comparison)
    if neutral_opening_position:
        # Preserve Tachiai Power, Momentum, cards and turn order; isolate
        # only the positional advantage carried into Exchange.
        state.position = 0
    available = {Side.A: set(), Side.B: set()}
    played = {Side.A: set(), Side.B: set()}
    if state.winner is None:
        state.active_side = first_exchange_side(
            comparison, state.fighter_a.wrestler, state.fighter_b.wrestler
        )
    try:
        for _ in range(max_turns):
            if state.winner is not None:
                break
            side = state.active_side
            start_exchange_turn(state, side, comparison)
            if state.winner is not None:
                break
            available[side].update(card.name for card in state.fighter(side).hand)
            before = len(state.card_plays)
            play_personality_turn(state, side, comparison)
            played[side].update(
                name for owner, name in state.card_plays[before:] if owner is side
            )
            if state.winner is not None:
                break
            end_exchange_turn(state, side)
        error = None if state.winner is not None else "turn limit"
    except (ValueError, KeyError, NotImplementedError, RuntimeError) as exc:
        error = type(exc).__name__ + ": " + str(exc)
    return state, available, played, error


def round_robin_pairs(config_count: int, seed: int):
    """Every round pairs every config once; all opponents occur exactly once."""
    if config_count < 2 or config_count % 2:
        raise ValueError("Round-robin requires an even number of configurations")
    players = list(range(config_count))
    random.Random(seed).shuffle(players)
    pairs = []
    for _ in range(config_count - 1):
        for index in range(config_count // 2):
            pairs.append((players[index], players[-1 - index]))
        # Circle method: hold the first player fixed and rotate the rest.
        players = [players[0], players[-1], *players[1:-1]]
    return pairs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repetitions", type=int, default=1,
                        help="Mirrored bouts per distinct pairing, per repetition")
    parser.add_argument("--max-turns", type=int, default=100)
    parser.add_argument("--max-pairs", type=int, default=None,
                        help="Number of unique round-robin pairs (3000 pairs = 6000 mirrored bouts)")
    parser.add_argument("--output-dir", default="big_test_artifacts")
    parser.add_argument("--seed", type=int, default=20261008)
    parser.add_argument("--batch-id", type=int, default=0)
    parser.add_argument("--neutral-opening-position", action="store_true",
                        help="Reset Position to 0 after Tachiai, before Exchange")
    args = parser.parse_args()
    if args.batch_id < 0:
        parser.error("--batch-id must be >= 0")
    if args.max_pairs is not None and args.max_pairs < 1:
        parser.error("--max-pairs must be >= 1")
    if args.repetitions < 1:
        parser.error("--repetitions must be >= 1")
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    configs = roster()
    assert len(configs) == 108
    schedule = round_robin_pairs(len(configs), args.seed)
    selected_pairs = schedule[:args.max_pairs]
    planned_bouts = args.repetitions * len(selected_pairs) * 2
    bouts = Counter()
    wins = Counter()
    cards = defaultdict(lambda: Counter())
    errors = Counter()
    outcomes = Counter()
    assignments = defaultdict(Counter)
    cohorts = defaultdict(Counter)
    advantage_results = defaultdict(Counter)
    kimarite_origins = defaultdict(Counter)
    played_origins = defaultdict(Counter)
    started_at = time.monotonic()
    actual_plays = Counter()
    opening_uses = Counter()
    finish_events = Counter()

    with (output / "bouts.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(("batch_id", "a", "b", "seed", "winner", "method",
                         "win_category", "winning_card_origin", "winner_grip",
                         "turns", "error", "a_stats", "a_priorities", "a_kimarite",
                         "a_start_card", "a_top_card", "b_stats", "b_priorities",
                         "b_kimarite", "b_start_card", "b_top_card",
                         "power_advantage_a", "technique_advantage_a",
                         "spirit_advantage_a"))
        for repeat in range(args.repetitions):
            for pair_idx, (i, j) in enumerate(selected_pairs):
                for orientation, (left, right) in enumerate(((i, j), (j, i))):
                    seed = args.seed + args.batch_id * 1_000_000_000 + repeat * 20000 + pair_idx * 2 + orientation
                    a, b = configs[left], configs[right]
                    state, available, played, error = run_one(
                        a, b, seed, args.max_turns,
                        neutral_opening_position=args.neutral_opening_position,
                    )
                    errors[error or "completed"] += 1
                    processed = sum(errors.values())
                    if processed % 500 == 0 or processed == planned_bouts:
                        elapsed = time.monotonic() - started_at
                        remaining = elapsed * (planned_bouts - processed) / processed
                        print(
                            f"{processed:,}/{planned_bouts:,} bouts "
                            f"({100 * processed / planned_bouts:.1f}%) "
                            f"elapsed {elapsed:.0f}s, ETA {remaining:.0f}s",
                            flush=True,
                        )
                    winner = state.winner
                    winner_grip = state.fighter(winner).total_grip if winner else None
                    if winner is None:
                        category = "incomplete"
                    elif state.win_source == "ringout":
                        category = "ringout_with_grip" if winner_grip else "ringout_without_grip"
                    elif state.win_source == "kimarite":
                        category = "kimarite:" + (state.win_method or "unknown")
                    elif state.win_method == "Exhaustion":
                        category = "deck_exhaustion"
                    elif state.win_method == "Power":
                        category = "no_power"
                    else:
                        category = "other:" + (state.win_method or "unknown")
                    outcomes[category] += 1
                    wa, wb = state.fighter_a.wrestler, state.fighter_b.wrestler
                    comparison = compare_tachiai(wa, wb)
                    winning_card_origin = ""
                    if state.win_source == "kimarite" and winner is not None:
                        winning_id = state.winning_kimarite_card_id
                        if winning_id is None:
                            raise AssertionError("Winning Kimarite has no card ID")
                        winning_card_origin = card_origin(
                            state.fighter(winner).wrestler, winning_id
                        )
                        kimarite_origins[(state.win_method, winning_card_origin)]["wins"] += 1
                        finish_events[(state.win_method, winning_card_origin)] += 1
                    def metadata(w):
                        return (
                            "/".join(map(str, (w.base_power, w.base_technique, w.base_spirit))),
                            "/".join(x.value for x in (w.primary, w.secondary, w.tertiary)),
                            w.starting_kimarite.name,
                            w.prepared_tachiai_card.name,
                            w.top_of_deck_card.name,
                        )
                    writer.writerow((args.batch_id, a[0], b[0], seed,
                                     state.fighter(winner).wrestler.name if winner else "",
                                     state.win_method or "", category,
                                     winning_card_origin,
                                     winner_grip if winner is not None else "",
                                     state.turn_number, error or "",
                                     *metadata(wa), *metadata(wb),
                                     comparison.power_advantage_a,
                                     comparison.technique_advantage_a,
                                     comparison.spirit_advantage_a))
                    if state.winner is None:
                        continue
                    for side, config in ((Side.A, a), (Side.B, b)):
                        name, _, priority = config
                        won = state.winner is side
                        bouts[name] += 1
                        wins[name] += int(won)
                        for group in (("build", *config[1]), *(
                            (label, value) for label, value in
                            zip(("Power", "Technique", "Spirit"), config[1])
                        ), ("priority", *(x.value for x in priority))):
                            cohorts[group]["bouts"] += 1
                            cohorts[group]["wins"] += int(won)
                        for stat in (Stat.POWER, Stat.TECHNIQUE, Stat.SPIRIT):
                            adv = comparison.advantage_for(side, stat)
                            advantage_results[(stat.value, adv)]["bouts"] += 1
                            advantage_results[(stat.value, adv)]["wins"] += int(won)
                        wrestler = state.fighter(side).wrestler
                        played_ids = {
                            cid for owner, cid in state.card_play_ids if owner is side
                        }
                        lookup = {
                            c.card_id: c for c in (
                                wrestler.starting_kimarite,
                                wrestler.prepared_tachiai_card,
                                wrestler.top_of_deck_card, *CARD_POOL
                            )
                        }
                        # Count every Exchange play, not just distinct card IDs.
                        for owner, cid in state.card_play_ids:
                            if owner is side:
                                played_card = lookup[cid]
                                actual_plays[(played_card.name, card_origin(wrestler, cid))] += 1
                        # Prepared cards always participate in Tachiai through orbs;
                        # this is separate from later Exchange play.
                        opening_uses[wrestler.prepared_tachiai_card.name] += 1
                        for cid in played_ids:
                            card = lookup[cid]
                            key = (card.name, card_origin(wrestler, cid))
                            played_origins[key]["bouts"] += 1
                            played_origins[key]["wins"] += int(won)
                        for role, card in (
                            ("designated_kimarite", wrestler.starting_kimarite),
                            ("starting_card", wrestler.prepared_tachiai_card),
                            ("top_deck_card", wrestler.top_of_deck_card),
                        ):
                            assignments[(role, card.name)]["bouts"] += 1
                            assignments[(role, card.name)]["wins"] += int(won)
                        # Cards may be in hand multiple turns: count each card
                        # once per wrestler-bout, separating played from unplayed.
                        for card in available[side]:
                            kind = "played" if card in played[side] else "hand_unplayed"
                            for slot, stat in enumerate(priority, start=1):
                                key = (card, kind, slot, stat.value)
                                cards[key]["bouts"] += 1
                                cards[key]["wins"] += int(won)

    with (output / "card_activity.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(("event", "card", "origin", "count"))
        for (role, card), tally in sorted(assignments.items()):
            writer.writerow(("assignment", card, role, tally["bouts"]))
        for card, count in sorted(opening_uses.items()):
            writer.writerow(("tachiai_prepared_use", card, "prepared_tachiai", count))
        for (card, origin), count in sorted(actual_plays.items()):
            writer.writerow(("exchange_play", card, origin, count))
        for (card, origin), count in sorted(played_origins.items()):
            writer.writerow(("exchange_bout_with_card", card, origin, count["bouts"]))
        for (card, origin), count in sorted(finish_events.items()):
            writer.writerow(("kimarite_finish", card, origin, count))
    assert sum(opening_uses.values()) == 2 * errors["completed"]
    assert sum(tally["bouts"] for (role, card), tally in assignments.items() if role == "starting_card") == sum(opening_uses.values())

    with (output / "kimarite_finishes_by_origin.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(("kimarite", "origin", "finishes"))
        for (card, origin), count in sorted(kimarite_origins.items()):
            writer.writerow((card, origin, count["wins"]))
    with (output / "card_play_by_origin.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(("card", "origin", "bouts_played", "wins", "win_rate"))
        for (card, origin), count in sorted(played_origins.items()):
            n = count["bouts"]
            writer.writerow((card, origin, n, count["wins"],
                             count["wins"] / n if n else ""))
    with (output / "stat_advantages.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(("stat", "signed_advantage", "bouts", "wins", "win_rate"))
        for (stat, advantage), count in sorted(advantage_results.items()):
            n = count["bouts"]
            writer.writerow((stat, advantage, n, count["wins"],
                             count["wins"] / n if n else ""))

    with (output / "wrestlers.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(("wrestler", "power", "technique", "spirit",
                         "primary", "secondary", "tertiary", "bouts", "wins", "win_rate"))
        for name, stats, priority in configs:
            n = bouts[name]
            writer.writerow((name, *stats, *(p.value for p in priority),
                             n, wins[name], wins[name] / n if n else ""))
    with (output / "cards.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(("card", "outcome", "priority_slot", "priority_stat",
                         "bouts", "wins", "win_rate"))
        for key, tally in sorted(cards.items(), key=lambda x: x[0][:3]):
            n = tally["bouts"]
            writer.writerow((*key, n, tally["wins"], tally["wins"] / n if n else ""))
    with (output / "card_assignments.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(("role", "card", "bouts", "wins", "win_rate"))
        for key, tally in sorted(assignments.items()):
            n = tally["bouts"]
            writer.writerow((*key, n, tally["wins"], tally["wins"] / n))
    with (output / "wrestler_cohorts.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(("group", "value_1", "value_2", "value_3", "bouts", "wins", "win_rate"))
        for key, tally in sorted(cohorts.items(), key=lambda item: str(item[0])):
            n = tally["bouts"]
            writer.writerow((*key, *([""] * (4 - len(key))), n, tally["wins"], tally["wins"] / n))
    with (output / "win_conditions.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(("win_category", "bouts"))
        writer.writerows(sorted(outcomes.items()))
    summary = {
        "configs": len(configs),
        "batch_id": args.batch_id,
        "seed_range_start": args.seed + args.batch_id * 1_000_000_000,
        "seed_range_end": args.seed + args.batch_id * 1_000_000_000 + (args.repetitions - 1) * 20000 + 11555,
        "planned_bouts": planned_bouts,
        "completed": errors["completed"],
        "neutral_opening_position": args.neutral_opening_position,
        "pairing_method": "balanced_round_robin",
        "unique_pairs_per_repetition": len(selected_pairs),
        "errors": dict(errors),
        "win_conditions": dict(outcomes),
        "card_activity": {
            "prepared_tachiai_uses": sum(opening_uses.values()),
            "exchange_plays": sum(actual_plays.values()),
            "distinct_card_per_bout_exchange_appearances": sum(t["bouts"] for t in played_origins.values()),
            "kimarite_finishes": sum(finish_events.values()),
        },
        "kimarite_finishes_by_origin": {
            f"{card}|{origin}": count["wins"]
            for (card, origin), count in sorted(kimarite_origins.items())
        },
        "repetitions": args.repetitions,
        "seed": args.seed,
        "max_turns": args.max_turns,
        "notes": "Per-card hand exposure counts distinct card names per wrestler-bout; played counts if played at least once. Priority slot describes wrestler AI preference, not card order. Excludes incomplete bouts from win rates.",
    }
    assert sum(outcomes.values()) == planned_bouts
    assert sum(errors.values()) == planned_bouts
    assert sum(bouts.values()) == 2 * errors["completed"]
    assert sum(c["bouts"] for c in advantage_results.values()) == 6 * errors["completed"]
    assert sum(c["wins"] for c in kimarite_origins.values()) == sum(
        count for category, count in outcomes.items()
        if category.startswith("kimarite:")
    )
    assert not any(key.startswith("other:") for key in outcomes), outcomes
    (output / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
