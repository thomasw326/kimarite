"""B12: source-locked 60 decks, 15 existing style AIs x four frameworks.

The 28-base and 40-maximum modes use the same 60 frameworks. Seeds and pair
indices are independent of shard count; every unordered pairing is mirrored.
Raw bout JSONL is the audit trail from which ALL aggregate rates are derived.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import Counter
from itertools import combinations
from pathlib import Path

import kimarite.style_ai_v5 as style_ai
from kimarite.b11_player_draft import AVAILABLE, GENERATED_ONLY, MAX_KIMARITE, MIN_KIMARITE
from kimarite.catalog import card_by_name
from kimarite.models import BoutState, Card, FighterState, Side, Stat, Wrestler
from kimarite.styles_v5 import STYLES
from kimarite.tachiai import compare_tachiai, first_exchange_side
from kimarite.tachiai_effects import resolve_prepared_tachiai
from kimarite.turns import apply_initial_power, end_exchange_turn, start_exchange_turn

SOURCE = Path(__file__).resolve().parents[1] / "data" / "b12_60_framework_decks.json"
AI_GROUPS = (
    "Mountain", "The Arsenal", "The Specialist", "Heavy Hitter", "Bulldozer",
    "Charger", "Pressure Fighter", "Power Grappler", "Unorthodox Powerhouse",
    "The Technician", "Mawashi Specialist", "Opportunist", "Fast Grappler",
    "Disruptor", "Speed Demon",
)


def load_designs(mode: str) -> list[dict]:
    if mode not in ("base28", "max40"):
        raise ValueError("Choose base28 or max40")
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    frameworks = source["frameworks"]
    if len(frameworks) != 60:
        raise ValueError("Expected exactly 60 frameworks")
    for i, row in enumerate(frameworks):
        if row["id"] != f"{i+1:02d}":
            raise ValueError(f"Framework order/number mismatch at {i}")
        if row["style_proxy"] != AI_GROUPS[i // 4] or row["style_proxy"] not in STYLES:
            raise ValueError(f"{row['id']}: bad 15-by-4 AI mapping")
        base, dupes = row["base"], row["duplicates"]
        if len(base) != 28 or len(set(base)) != 28:
            raise ValueError(f"{row['id']}: base must have 28 distinct cards")
        if len(dupes) != 12 or len(set(dupes)) != 12 or not set(dupes) <= set(base):
            raise ValueError(f"{row['id']}: duplicates must be 12 distinct base selections")
        if row["starting_kimarite"] not in base or not card_by_name(row["starting_kimarite"]).is_kimarite:
            raise ValueError(f"{row['id']}: starting Kimarite not in base")
        if any(name not in AVAILABLE or name in GENERATED_ONLY for name in base + dupes):
            raise ValueError(f"{row['id']}: unavailable or generated-only card")
        kim_count = sum(card_by_name(name).is_kimarite for name in base)
        if not MIN_KIMARITE <= kim_count <= MAX_KIMARITE:
            raise ValueError(f"{row['id']}: invalid Kimarite count {kim_count}")
        row["cards"] = base + (dupes if mode == "max40" else [])
        row["name"] = f"{row['id']} — {row['identity']}"
    return frameworks


def source_checksum() -> str:
    return hashlib.sha256(SOURCE.read_bytes()).hexdigest()


def make_seed(master: int, pair_index: int, repeat: int, framework: str) -> int:
    raw = f"b12:{master}:{pair_index}:{repeat}:{framework}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(raw).digest()[:8], "big")


def physical_card(name: str) -> Card:
    card = card_by_name(name)
    # Physical instances are individually allocated rather than sharing
    # catalogue objects. Their rules/card_id remain untouched.
    return Card(card.card_id, card.name, card.power, card.technique,
                card.spirit, card.is_kimarite)


def make_fighter(entry: dict, seed: int, ranking: int):
    rng = random.Random(seed)
    physical = [physical_card(name) for name in entry["cards"]]
    slot_index = next(i for i, c in enumerate(physical)
                      if c.name == entry["starting_kimarite"])
    starting = physical.pop(slot_index)
    ordinary = [c for c in physical if not c.is_kimarite]
    if len(ordinary) < 2:
        raise ValueError(f"{entry['name']}: cannot assign prepared/top ordinary cards")
    # Uniform random over eligible PHYSICAL copies; names must be different.
    prepared = rng.choice(ordinary)
    physical.remove(prepared)
    top = rng.choice([c for c in physical if not c.is_kimarite and c.name != prepared.name])
    physical.remove(top)
    rng.shuffle(physical)
    style = STYLES[entry["style_proxy"]]
    order = list(dict.fromkeys((style.primary, style.secondary)))
    order += [stat.value for stat in (Stat.POWER, Stat.TECHNIQUE, Stat.SPIRIT)
              if stat.value not in order]
    wrestler = Wrestler(entry["name"], *style.stats, starting, prepared, top,
                        primary=Stat(order[0]), secondary=Stat(order[1]),
                        tertiary=Stat(order[2]), ranking=ranking)
    fighter = FighterState(wrestler, draw_pile=[top, *physical],
                           kimarite_zone=[starting])
    # Record card provenance by physical identity, not by name/card_id.
    origins = {id(starting): "starting_kimarite", id(prepared): "prepared_tachiai",
               id(top): "top_deck"}
    origins.update({id(c): "deck" for c in physical})
    return fighter, origins


def take_snapshot(state: BoutState, side: Side) -> dict:
    me, foe = state.fighter(side), state.opponent(side)
    sign = state.sign(side)
    return {
        "push_position": state.position * sign,
        "momentum": state.momentum * sign,
        "power": me.power,
        "foe_power": foe.power,
        "grip": me.total_grip,
        "foe_grip": foe.total_grip,
        "hand": len(me.hand),
        "draw_pile": len(me.draw_pile),
        "foe_draw_pile": len(foe.draw_pile),
        "discard": len(me.discard_pile),
        "foe_discard": len(foe.discard_pile),
        "plays_remaining": me.plays_remaining,
    }


def delta(before: dict, after: dict) -> dict:
    return {key: after[key] - before[key] for key in before}


def run_one(entries: list[dict], x: int, y: int, seed: int, pair_id: int,
            repetition: int, max_turns: int, mode: str):
    a, b = entries[x], entries[y]
    fighter_a, origins_a = make_fighter(a, make_seed(seed, pair_id, repetition, a["id"]), 1)
    fighter_b, origins_b = make_fighter(b, make_seed(seed, pair_id, repetition, b["id"]), 2)
    state = BoutState(fighter_a, fighter_b)
    provenance = {Side.A: origins_a, Side.B: origins_b}
    comparison = compare_tachiai(fighter_a.wrestler, fighter_b.wrestler)
    records = {
        side: {"plays": [], "seen_hand": set(), "held_end_turn": set(),
               "kept_at_turn_start": Counter(), "turns_played": 0}
        for side in (Side.A, Side.B)
    }
    original = style_ai.play_card

    def monitored_play(s, side, card, *, context=None):
        # Style AI simulates candidate plays on deep copies. Only actual
        # live-state plays count. Never count lookahead trials as actions.
        if s is not state:
            return original(s, side, card, context=context)
        before = take_snapshot(state, side)
        result = original(s, side, card, context=context)
        after = take_snapshot(state, side)
        records[side]["plays"].append({
            "card": card.name,
            "origin": provenance[side].get(id(card), "generated"),
            "turn": state.turn_number,
            "delta": delta(before, after),
        })
        records[side]["seen_hand"].update(c.name for c in state.fighter(side).hand)
        return result

    error = None
    try:
        apply_initial_power(state, comparison)
        resolve_prepared_tachiai(state, comparison)
        opening = {
            "power_advantage_a": comparison.power_advantage_a,
            "technique_advantage_a": comparison.technique_advantage_a,
            "spirit_advantage_a": comparison.spirit_advantage_a,
            "push_position_a": state.position,
            "momentum_a": state.momentum,
        }
        if state.winner is None:
            state.active_side = first_exchange_side(comparison, fighter_a.wrestler,
                                                    fighter_b.wrestler)
            opening["first_exchange_side"] = state.active_side.value
        else:
            opening["first_exchange_side"] = None
        for side in (Side.A, Side.B):
            records[side]["seen_hand"].update(c.name for c in state.fighter(side).hand)
        style_ai.play_card = monitored_play
        for _ in range(max_turns):
            if state.winner is not None:
                break
            side = state.active_side
            gained = start_exchange_turn(state, side, comparison)
            records[side]["turns_played"] += 1
            records[side]["kept_at_turn_start"].update(c.name for c in gained)
            records[side]["seen_hand"].update(c.name for c in state.fighter(side).hand)
            if state.winner is not None:
                break
            style_ai.play_style_turn(state, side, comparison,
                                     entries[x if side is Side.A else y]["style_proxy"])
            records[side]["seen_hand"].update(c.name for c in state.fighter(side).hand)
            records[side]["held_end_turn"].update(c.name for c in state.fighter(side).hand)
            if state.winner is not None:
                break
            end_exchange_turn(state, side)
        if state.winner is None:
            error = "turn_limit"
    except (ValueError, KeyError, RuntimeError, NotImplementedError) as exc:
        error = f"{type(exc).__name__}: {exc}"
    finally:
        style_ai.play_card = original

    winner_side = state.winner
    winning_origin = None
    if state.win_source == "kimarite" and winner_side is not None:
        # The engine chooses the earliest satisfied same-name Kimarite.
        # Physical origin distinguishes the starting copy from a deck copy.
        matches = [c for c in state.fighter(winner_side).kimarite_zone
                   if c.name == state.win_method]
        if matches:
            winning_origin = provenance[winner_side].get(id(matches[0]), "generated")
    fighters = {}
    for side, entry, fighter in ((Side.A, a, fighter_a), (Side.B, b, fighter_b)):
        usage = records[side]
        fighters[side.value] = {
            "framework": entry["id"],
            "ai_style": entry["style_proxy"],
            "starting_kimarite": fighter.wrestler.starting_kimarite.name,
            "prepared_tachiai": fighter.wrestler.prepared_tachiai_card.name,
            "top_deck": fighter.wrestler.top_of_deck_card.name,
            "deck": list(entry["cards"]),
            "plays": usage["plays"],
            "seen_hand": sorted(usage["seen_hand"]),
            "held_end_turn": sorted(usage["held_end_turn"]),
            "kept_at_turn_start": dict(usage["kept_at_turn_start"]),
            "turns_played": usage["turns_played"],
        }
    return {
        "schema": "b12-bout-v1",
        "pair_id": pair_id,
        "repetition": repetition,
        "mode": mode,
        "master_seed": seed,
        "framework_a": a["id"],
        "framework_b": b["id"],
        "winner_side": winner_side.value if winner_side else None,
        "win_method": state.win_method,
        "win_source": state.win_source,
        "winning_kimarite_origin": winning_origin,
        "turns": state.turn_number,
        "error": error,
        "opening": opening,
        "fighters": fighters,
        "temporary_outcomes": [
            {"side": side.value, "card": card, "outcome": outcome}
            for side, card, outcome in state.temporary_outcomes
        ],
    }


def schedule(smoke: bool = False):
    if smoke:
        return [(i, i + 1) for i in range(0, 60, 2)]
    return list(combinations(range(60), 2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("base28", "max40"), default="max40")
    parser.add_argument("--seed", type=int, default=20261102)
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--shards", type=int, default=1)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--max-turns", type=int, default=100)
    parser.add_argument("--output-dir", default="artifacts/b12_60")
    args = parser.parse_args()
    entries = load_designs(args.mode)
    if args.shards < 1 or not 0 <= args.shard_index < args.shards:
        parser.error("shard index must be in 0..shards-1")
    if args.repetitions < 1:
        parser.error("repetitions must be positive")
    pairs = schedule(args.smoke)
    total = len(pairs) * 2 * args.repetitions
    print(json.dumps({
        "status": "validated", "mode": args.mode, "frameworks": len(entries),
        "ai_styles": len({e["style_proxy"] for e in entries}),
        "physical_cards_per_deck": len(entries[0]["cards"]),
        "source_sha256": source_checksum(),
        "pairs": len(pairs), "total_bouts_all_shards": total,
    }), flush=True)
    if args.validate_only:
        return
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    completed = errors = attempts = 0
    path = output / f"bouts_{args.mode}_shard{args.shard_index:02d}.jsonl"
    with path.open("w", encoding="utf-8") as stream:
        for global_id in range(total):
            if global_id % args.shards != args.shard_index:
                continue
            pair_idx = (global_id // 2) % len(pairs)
            repetition = (global_id // 2) // len(pairs)
            x, y = pairs[pair_idx]
            if global_id % 2:
                x, y = y, x
            record = run_one(entries, x, y, args.seed, pair_idx, repetition,
                             args.max_turns, args.mode)
            record["global_id"] = global_id
            record["source_sha256"] = source_checksum_value
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
            attempts += 1
            if record["error"] is None and record["winner_side"] is not None:
                completed += 1
            else:
                errors += 1
            if attempts % 25 == 0:
                print(f"{args.mode} shard {args.shard_index}: {attempts} bouts, errors={errors}",
                      flush=True)
    print(json.dumps({"requested": attempts, "completed": completed,
                      "errors": errors, "file": str(path)}), flush=True)
    if errors or completed != attempts:
        raise SystemExit(1)


if __name__ == "__main__":
    source_checksum_value = source_checksum()
    main()
