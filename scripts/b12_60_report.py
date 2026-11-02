"""Aggregate reproducible B12 per-bout events into framework/card diagnostics.

All percentages include wins and completed wrestler-bout denominators. Raw
bout JSONL remains the source of truth. Never count incomplete bouts as losses.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


def tally():
    return {"bouts": 0, "wins": 0}


def add(store, key, won, weight=1):
    t = store[key]
    t["bouts"] += weight
    t["wins"] += int(won) * weight


def percent(w, n):
    return "" if not n else round(100 * w / n, 3)


def write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def scored_row(labels, t):
    n = t["bouts"]
    w = t["wins"]
    return {**labels, "wins": w, "bouts": n,
            "win_rate_percent": percent(w, n), "low_sample_n_lt_30": n < 30}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input-root", default="artifacts/b12_shards")
    p.add_argument("--output-dir", default="artifacts/b12_report")
    p.add_argument("--repetitions", type=int, default=1)
    p.add_argument("--allow-partial", action="store_true")
    args = p.parse_args()
    output = Path(args.output_dir)
    files = sorted(Path(args.input_root).rglob("bouts_*.jsonl"))
    if not files:
        raise SystemExit("No bout files found")

    framework = defaultdict(tally)
    matchup = defaultdict(tally)
    method = defaultdict(tally)
    assigned = defaultdict(tally)
    played = defaultdict(tally)
    included = defaultdict(tally)
    exposure = defaultdict(tally)
    starting_kim = defaultdict(tally)
    deck_kim = defaultdict(tally)
    finishes = defaultdict(tally)
    contributions = defaultdict(Counter)
    temporaries = defaultdict(Counter)
    timing = defaultdict(Counter)
    status = Counter()
    seen_global_ids = defaultdict(set)
    pair_directions = defaultdict(set)
    source_hashes = set()
    errors = []
    total = 0
    all_win_methods = Counter()

    for file in files:
        for line in file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            bout = json.loads(line)
            total += 1
            mode = bout["mode"]
            global_id = bout["global_id"]
            if global_id in seen_global_ids[mode]:
                raise SystemExit(f"Duplicate bout: {mode}/{global_id}")
            seen_global_ids[mode].add(global_id)
            source_hashes.add(bout["source_sha256"])
            status[(mode, "requested")] += 1
            pair_directions[(mode, bout["pair_id"], bout["repetition"])].add(
                (bout["framework_a"], bout["framework_b"]))
            if bout["error"] or bout["winner_side"] is None:
                errors.append({"mode": mode, "global_id": global_id,
                               "error": bout["error"] or "no winner"})
                status[(mode, "failed")] += 1
                continue
            status[(mode, "completed")] += 1
            win_side = bout["winner_side"]
            win_method = bout["win_method"] or ""
            win_source = bout["win_source"] or "unknown"
            all_win_methods[(mode, win_source, win_method)] += 1
            winner_framework = bout["fighters"][win_side]["framework"]
            finish_card = (win_method if win_source == "kimarite" else "")
            if finish_card and not bout["winning_kimarite_origin"]:
                raise SystemExit(f"Missing physical finishing instance origin: {mode}/{global_id}")
            for side in ("A", "B"):
                f = bout["fighters"][side]
                frm = f["framework"]
                enemy = bout["fighters"]["B" if side == "A" else "A"]["framework"]
                won = (side == win_side)
                add(framework, (mode, frm), won)
                add(matchup, (mode, frm, enemy, side), won)
                add(method, (mode, frm, win_source, win_method), won)
                add(assigned, (mode, frm, "prepared_tachiai", f["prepared_tachiai"]), won)
                add(assigned, (mode, frm, "top_deck", f["top_deck"]), won)
                add(assigned, (mode, frm, "starting_kimarite", f["starting_kimarite"]), won)
                add(starting_kim, (mode, frm, f["starting_kimarite"]), won)
                timing[(mode, frm)]["bouts"] += 1
                timing[(mode, frm)]["turn_total"] += bout["turns"]
                timing[(mode, frm)]["win_turn_total"] += bout["turns"] if won else 0
                timing[(mode, frm)]["wins"] += int(won)
                for card_name in set(f["deck"]):
                    copies = f["deck"].count(card_name)
                    copy_label = f"{copies}-copy"
                    add(included, (mode, frm, card_name, copy_label), won)
                plays_by_name = Counter(event["card"] for event in f["plays"])
                play_origin_pairs = {(event["card"], event["origin"]) for event in f["plays"]}
                for card_name in set(f["deck"]):
                    group = "played" if card_name in plays_by_name else "unplayed"
                    add(played, (mode, frm, card_name, group), won)
                for card_name, play_count in plays_by_name.items():
                    # Also tracks generated cards absent from the actual deck.
                    add(played, (mode, frm, card_name, "played_any_origin"), won)
                    contributions[(mode, frm, card_name)]["plays"] += play_count
                for event in f["plays"]:
                    key = (mode, frm, event["card"])
                    c = contributions[key]
                    d = event["delta"]
                    c["push"] += d["push_position"]
                    c["momentum"] += d["momentum"]
                    c["own_power"] += d["power"]
                    c["opponent_power"] += -d["foe_power"]
                    c["own_grip"] += d["grip"]
                    c["opponent_grip_removed"] += -d["foe_grip"]
                    c["net_hand_change"] += d["hand"]
                    c["own_deck_depleted"] += -d["draw_pile"]
                    c["opponent_deck_depleted"] += -d["foe_draw_pile"]
                    c["own_discard_increase"] += d["discard"]
                    c["opponent_discard_increase"] += d["foe_discard"]
                    # One play is normally spent; nonnegative bonus is an actual
                    # play refund, while negatives expose extra costs.
                    c["extra_plays_net"] += d["plays_remaining"] + 1
                for card_name, origin in play_origin_pairs:
                    if card_name != f["starting_kimarite"] or origin != "starting_kimarite":
                        add(deck_kim, (mode, frm, card_name, origin), won)
                for card_name in f["seen_hand"]:
                    add(exposure, (mode, frm, card_name, "seen_in_hand"), won)
                for card_name in f["held_end_turn"]:
                    add(exposure, (mode, frm, card_name, "held_end_of_turn"), won)
                for card_name in f["kept_at_turn_start"]:
                    add(exposure, (mode, frm, card_name, "kept_at_turn_start"), won)
                for metric, value in (("power_advantage", bout["opening"]["power_advantage_a"]),
                                      ("technique_advantage", bout["opening"]["technique_advantage_a"]),
                                      ("spirit_advantage", bout["opening"]["spirit_advantage_a"])):
                    status[(mode, "tachiai", frm, metric, value if side == "A" else -value, won)] += 1
                if finish_card and won:
                    orig = bout["winning_kimarite_origin"]
                    finishes[(mode, frm, finish_card, orig)]["finishes"] += 1
            for event in bout["temporary_outcomes"]:
                frm = bout["fighters"][event["side"]]["framework"]
                temporaries[(mode, frm, event["card"])][event["outcome"]] += 1

    if len(source_hashes) != 1:
        raise SystemExit(f"Deck source checksum mismatch: {len(source_hashes)} different sources")
    if args.repetitions < 1:
        raise SystemExit("repetitions must be positive")
    if not args.allow_partial:
        expected = 3540 * args.repetitions
        for mode in ("base28", "max40"):
            if len(seen_global_ids[mode]) != expected:
                raise SystemExit(f"{mode}: {len(seen_global_ids[mode])}/{expected} expected bouts")
            if seen_global_ids[mode] != set(range(expected)):
                raise SystemExit(f"{mode}: global_id gaps or out-of-range IDs")
        if errors:
            raise SystemExit(f"Simulation errors: {errors[:10]}")
        if any(len(directions) != 2 for directions in pair_directions.values()):
            raise SystemExit("Some matchups are not mirrored exactly once")

    def dump_store(filename, field_names, store):
        fields = [*field_names, "wins", "bouts", "win_rate_percent", "low_sample_n_lt_30"]
        rows = [scored_row(dict(zip(field_names, key)), val)
                for key, val in sorted(store.items())]
        write_csv(output / filename, fields, rows)

    dump_store("framework_results.csv", ["mode", "framework"], framework)
    dump_store("matchup_results.csv", ["mode", "framework", "opponent", "side"], matchup)
    dump_store("victory_methods.csv", ["mode", "framework", "source", "method"], method)
    dump_store("card_assignments.csv", ["mode", "framework", "role", "card"], assigned)
    dump_store("card_played_vs_unplayed.csv", ["mode", "framework", "card", "play_status"], played)
    dump_store("card_inclusion.csv", ["mode", "framework", "card", "copies"], included)
    dump_store("hand_exposure.csv", ["mode", "framework", "card", "type"], exposure)
    dump_store("starting_kimarite_performance.csv", ["mode", "framework", "kimarite"], starting_kim)
    dump_store("card_origin_play_rates.csv", ["mode", "framework", "card", "origin"], deck_kim)

    # Finish share and starting-vs-deck provenance must not be conflated with
    # winning a bout in which the card happened to be available/played.
    finish_rows = []
    for (mode, frm, card, origin), val in sorted(finishes.items()):
        n_wins = framework[(mode, frm)]["wins"]
        finish_rows.append({"mode": mode, "framework": frm, "kimarite": card,
                            "origin": origin, "finishes": val["finishes"],
                            "framework_wins": n_wins,
                            "share_of_framework_victories_percent": percent(val["finishes"], n_wins),
                            "low_sample_n_lt_30": n_wins < 30})
    write_csv(output / "kimarite_finishes_by_origin.csv",
              ["mode", "framework", "kimarite", "origin", "finishes",
               "framework_wins", "share_of_framework_victories_percent",
               "low_sample_n_lt_30"], finish_rows)

    contribution_rows = [{"mode": m, "framework": f, "card": c, **vals}
                         for (m, f, c), vals in sorted(contributions.items())]
    fields = ["mode", "framework", "card", "plays", "push", "momentum", "own_power",
              "opponent_power", "own_grip", "opponent_grip_removed", "net_hand_change",
              "own_deck_depleted", "opponent_deck_depleted", "own_discard_increase",
              "opponent_discard_increase", "extra_plays_net"]
    write_csv(output / "card_immediate_contributions.csv", fields, contribution_rows)

    temporary_rows = [{"mode": m, "framework": f, "card": c, **vals}
                      for (m, f, c), vals in sorted(temporaries.items())]
    temp_events = sorted({evt for vals in temporaries.values() for evt in vals})
    write_csv(output / "temporary_outcomes.csv",
              ["mode", "framework", "card", *temp_events], temporary_rows)

    timing_rows = [{"mode": mode, "framework": frm, **vals,
                    "avg_turns": round(vals["turn_total"] / vals["bouts"], 3)}
                   for (mode, frm), vals in sorted(timing.items())]
    write_csv(output / "game_length.csv",
              ["mode", "framework", "bouts", "wins", "turn_total",
               "win_turn_total", "avg_turns"], timing_rows)

    tachiai_rows = []
    for key, n in sorted(status.items(), key=lambda x: str(x[0])):
        if len(key) != 6 or key[1] != "tachiai":
            continue
        mode, _, frm, metric, advantage, won = key
        tachiai_rows.append({"mode": mode, "framework": frm, "metric": metric,
                             "advantage": advantage, "won": won, "bouts": n})
    write_csv(output / "tachiai_advantages.csv",
              ["mode", "framework", "metric", "advantage", "won", "bouts"], tachiai_rows)

    summary = {
        "source_sha256": next(iter(source_hashes)), "bouts_total": total,
        "modes": {mode: {"requested": status[(mode, "requested")],
                         "completed": status[(mode, "completed")],
                         "failed": status[(mode, "failed")],
                         "frameworks": len({fr for m, fr in framework if m == mode}),
                         "distinct_pairs": len({pair for m, pair, _ in pair_directions if m == mode})}
                  for mode in ("base28", "max40")},
        "win_sources": [{"mode": mode, "source": source, "method": method_name, "finishes": n}
                        for (mode, source, method_name), n in sorted(all_win_methods.items())],
        "errors": errors,
        "repetitions": args.repetitions,
        "low_sample_rule": "N<30 flagged; zero denominators blank",
        "note": "Association, not causation. Counts exclude incomplete bouts. Starting-role wins and real Kimarite finishes are distinct.",
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary["modes"], indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
