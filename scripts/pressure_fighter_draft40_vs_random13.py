"""Isolated 2,400-bout test: live Pressure Fighter draft40 vs FG/TT 27+13.

No catalogue, style, opponent 27-card core, AI, or rules changes.
Pressure Fighter only: a fixed 40-copy physical deck, including YOR-C1.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

import three_style_random13_audit as baseline

ROOT = Path(__file__).resolve().parents[1]
DECK_FILE = ROOT / "data" / "pressure_fighter_draft40_20261012.json"
STYLES = ("Pressure Fighter", "Fast Grappler", "The Technician")
PAIRS = (("Pressure Fighter", "Fast Grappler"),
         ("Pressure Fighter", "The Technician"))
BASE_SEED = 20261013
TOTAL_REPETITIONS = 600
SCHEDULED = TOTAL_REPETITIONS * len(PAIRS) * 2
SHARD_SIZE = 150
BOUT_FIELDS = (
    "repetition", "pair_index", "seat_a", "seat_b", "seed",
    "completed", "winner", "method", "source", "turns", "error",
    "a_starting_kimarite", "b_starting_kimarite",
    "a_prepared_tachiai", "b_prepared_tachiai",
    "a_top_deck", "b_top_deck",
    "a_random13", "b_random13",
    "a_cards_played", "b_cards_played",
)
EVENT_FIELDS = (
    "style", "opponent", "card",
    "deck_bouts", "deck_copies", "played_bouts",
    "played_uses", "played_wins", "finisher_wins",
    "random_bouts", "random_played_bouts",
)

def snapshot():
    data = json.loads(DECK_FILE.read_text(encoding="utf-8"))
    counts = data["copy_count"]
    assert len(counts) == 28 and sum(counts.values()) == 40
    assert counts["Yorikiri (YOR-C1)"] == 1 and counts["Shiko Stomp"] == 1
    assert all(isinstance(v, int) and v > 0 for v in counts.values())
    assert "Power Water Cantrip" not in counts
    return counts

def install():
    from kimarite import style_builds_v5, style_simulate_v5, style_ai_v5
    from kimarite.models import Card, FighterState, Stat, Wrestler
    from kimarite.r21_variant_rules import build_variant_card
    from kimarite.styles_v5 import STYLES as STYLE_PROFILES

    aliases = baseline.install()  # Real B7 roster, fixed FG/TT 27+13.
    opponent_builder = style_builds_v5.build_style
    aliases["R21:R21-YOR-C1"] = "Yorikiri (YOR-C1)"

    # The chosen C1 remains a true R21 variant with the original Grip
    # Exchange and win predicate, not a rename of B7's global C3.
    special = build_variant_card("R21-YOR-C1", card_id=99_901)
    assert special.name == "R21:R21-YOR-C1"
    chosen = snapshot()
    catalogue = {
        aliases.get(card.name, card.name): card
        for card in style_builds_v5.CARD_POOL
    }
    assert len(catalogue) == len(style_builds_v5.CARD_POOL)
    assert all(n in catalogue or n == "Yorikiri (YOR-C1)"
               for n in chosen)

    original_affinity = style_ai_v5.card_affinity
    def c1_affinity(style, name):
        return original_affinity(style, "Yorikiri"
                                 if name == special.name else name)
    style_ai_v5.card_affinity = c1_affinity

    def draft_or_opponent(style, seed=0, ranking=1, difficulty=0, *,
                          enable_stat_boosts=False):
        if style != "Pressure Fighter":
            return opponent_builder(style, seed=seed, ranking=ranking,
                                    difficulty=difficulty,
                                    enable_stat_boosts=enable_stat_boosts)
        assert difficulty == 0 and not enable_stat_boosts
        rng = random.Random(seed)
        source_cards = []
        for name, count in sorted(chosen.items()):
            template = special if name == "Yorikiri (YOR-C1)" else catalogue[name]
            source_cards.extend([template] * count)
        assert len(source_cards) == 40
        physical = [
            Card(4_000_000 + i, c.name, c.power, c.technique, c.spirit,
                 c.is_kimarite)
            for i, c in enumerate(source_cards)
        ]
        kimarite = sorted((c for c in physical if c.is_kimarite),
                          key=lambda c: (-c1_affinity(style, c.name), c.name))
        basic_by_name = {c.name: c for c in physical if not c.is_kimarite}
        basics = sorted(basic_by_name.values(),
                        key=lambda c: (-c1_affinity(style, c.name), c.name))
        assert len(kimarite) == 8 and len(basics) >= 10
        # Same B7 ranked and weighted opening selections as other wrestlers.
        starter = rng.choices(kimarite[:3], weights=(3, 2, 1))[0]
        prepared = rng.choices(basics[:10],
                               weights=tuple(range(10, 0, -1)))[0]
        top_candidates = [c for c in basics[:10] if c.name != prepared.name]
        assert len(top_candidates) == 9
        top = rng.choices(top_candidates,
                          weights=tuple(range(9, 0, -1)))[0]
        for c in (starter, prepared, top):
            physical.remove(c)
        rng.shuffle(physical)
        profile = STYLE_PROFILES[style]
        third = next(st for st in Stat
                     if st.value not in {profile.primary, profile.secondary})
        wrestler = Wrestler(
            style, *profile.stats, starter, prepared, top,
            primary=Stat(profile.primary), secondary=Stat(profile.secondary),
            tertiary=third, ranking=ranking,
        )
        fighter = FighterState(
            wrestler, draw_pile=[top, *physical], kimarite_zone=[starter])
        fighter.random_selected_names = ()
        inventory = [starter, prepared, *fighter.draw_pile]
        assert len(inventory) == 40
        assert len({c.card_id for c in inventory}) == 40
        actual = Counter(aliases.get(c.name, c.name) for c in inventory)
        assert dict(actual) == chosen, (actual, chosen)
        return style_builds_v5.StyleBuild(fighter, frozenset())

    style_builds_v5.build_style = draft_or_opponent
    style_simulate_v5.build_style = draft_or_opponent
    return aliases, draft_or_opponent

def canonical(name, alias):
    return alias.get(name, name)

def run(start, stop, output):
    from kimarite.models import Side
    from kimarite.style_simulate_v5 import run_style_bout
    aliases, builder = install()
    output.mkdir(parents=True, exist_ok=True)
    event_stats = defaultdict(Counter)
    completed = 0
    exceptions = []
    rows = []
    for repetition in range(start, stop):
        for pair_index, (first, second) in enumerate(PAIRS):
            seed = BASE_SEED + repetition * 10000 + pair_index
            for a, b in ((first, second), (second, first)):
                result = run_style_bout(
                    a, b, seed=seed, max_turns=100,
                    difficulty=0, experimental_final22=True,
                )
                state = result.state
                winner = a if state.winner is Side.A else (
                    b if state.winner is Side.B else "")
                rebuilt = {
                    Side.A: builder(a, seed=seed, ranking=1).fighter,
                    Side.B: builder(b, seed=seed + 1009, ranking=2).fighter,
                }
                lists = {}
                for side, style in ((Side.A, a), (Side.B, b)):
                    live = state.fighter(side)
                    initial = rebuilt[side]
                    assert (initial.wrestler.starting_kimarite.name ==
                            live.wrestler.starting_kimarite.name)
                    assert (initial.wrestler.prepared_tachiai_card.name ==
                            live.wrestler.prepared_tachiai_card.name)
                    assert (initial.wrestler.top_of_deck_card.name ==
                            live.wrestler.top_of_deck_card.name)
                    inventory = [initial.wrestler.starting_kimarite,
                                 initial.wrestler.prepared_tachiai_card,
                                 *initial.draw_pile]
                    assert len(inventory) == 40
                    copies = Counter(canonical(x.name, aliases)
                                     for x in inventory)
                    random_names = tuple(initial.random_selected_names)
                    assert (len(random_names) == 0 if style == "Pressure Fighter"
                            else len(random_names) == 13)
                    if style == "Pressure Fighter":
                        assert copies == Counter(snapshot())
                    else:
                        assert all(v == 1 for v in copies.values())
                        assert len(set(random_names)) == 13
                        assert set(random_names).issubset(copies)
                    lists[side] = (copies, random_names)
                a_plays = Counter(canonical(n, aliases)
                                  for side, n in state.card_plays
                                  if side is Side.A)
                b_plays = Counter(canonical(n, aliases)
                                  for side, n in state.card_plays
                                  if side is Side.B)
                record = {
                    "repetition": repetition, "pair_index": pair_index,
                    "seat_a": a, "seat_b": b, "seed": seed,
                    "completed": result.completed, "winner": winner,
                    "method": canonical(state.win_method or "", aliases),
                    "source": state.win_source or "", "turns": result.turns,
                    "error": result.unsupported_reason or "",
                    "a_starting_kimarite": canonical(
                        state.fighter_a.wrestler.starting_kimarite.name, aliases),
                    "b_starting_kimarite": canonical(
                        state.fighter_b.wrestler.starting_kimarite.name, aliases),
                    "a_prepared_tachiai": canonical(
                        state.fighter_a.wrestler.prepared_tachiai_card.name, aliases),
                    "b_prepared_tachiai": canonical(
                        state.fighter_b.wrestler.prepared_tachiai_card.name, aliases),
                    "a_top_deck": canonical(
                        state.fighter_a.wrestler.top_of_deck_card.name, aliases),
                    "b_top_deck": canonical(
                        state.fighter_b.wrestler.top_of_deck_card.name, aliases),
                    "a_random13": "; ".join(lists[Side.A][1]),
                    "b_random13": "; ".join(lists[Side.B][1]),
                    "a_cards_played": "; ".join(
                        f"{x} x{n}" for x, n in sorted(a_plays.items())),
                    "b_cards_played": "; ".join(
                        f"{x} x{n}" for x, n in sorted(b_plays.items())),
                }
                rows.append(record)
                if not result.completed or not winner or result.unsupported_reason:
                    exceptions.append(record)
                    continue
                completed += 1
                for side, style, opponent, plays in (
                    (Side.A, a, b, a_plays), (Side.B, b, a, b_plays)):
                    won = int(state.winner is side)
                    cards, random_names = lists[side]
                    for name, copies in cards.items():
                        for key in ((style, opponent, name), (style, "ALL", name)):
                            v = event_stats[key]
                            v["deck_bouts"] += 1
                            v["deck_copies"] += copies
                            if name in random_names:
                                v["random_bouts"] += 1
                            if name in plays:
                                v["played_bouts"] += 1
                                v["played_uses"] += plays[name]
                                v["played_wins"] += won
                                if name in random_names:
                                    v["random_played_bouts"] += 1
                            if won and state.win_source == "kimarite" and (
                                canonical(state.win_method, aliases) == name):
                                v["finisher_wins"] += 1

    assert len(rows) == (stop - start) * len(PAIRS) * 2
    with (output / "bouts.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=BOUT_FIELDS)
        w.writeheader()
        w.writerows(rows)
    with (output / "card_counts.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=EVENT_FIELDS)
        w.writeheader()
        for key, counts in sorted(event_stats.items()):
            w.writerow({**dict(zip(EVENT_FIELDS[:3], key)),
                        **{k: counts[k] for k in EVENT_FIELDS[3:]}})
    meta = {
        "range": [start, stop], "scheduled": len(rows),
        "completed": completed, "incomplete": len(exceptions),
        "pressure_fighter_copies": snapshot(),
        "opponents": "27 curated distinct + 13 freshly sampled distinct, per wrestler per bout",
        "yorikiri": "R21:R21-YOR-C1 (Pressure Fighter ONLY)",
        "shiko_stomp": "real Temporary defense (PR #18)",
    }
    (output / "manifest.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps({k: v for k, v in meta.items()
                      if k != "pressure_fighter_copies"}, indent=2), flush=True)

def report(root, output):
    output.mkdir(parents=True, exist_ok=True)
    shards = sorted(p for p in root.iterdir()
                    if p.is_dir() and (p / "manifest.json").exists())
    assert len(shards) == TOTAL_REPETITIONS // SHARD_SIZE
    ranges = set()
    all_rows = []
    totals = defaultdict(Counter)
    for shard in shards:
        meta = json.loads((shard / "manifest.json").read_text())
        a, b = meta["range"]
        assert b - a == SHARD_SIZE
        assert a not in ranges
        ranges.add(a)
        assert meta["scheduled"] == SHARD_SIZE * len(PAIRS) * 2
        assert meta["pressure_fighter_copies"] == snapshot()
        with (shard / "bouts.csv").open(newline="", encoding="utf-8") as f:
            lines = list(csv.DictReader(f))
            assert len(lines) == meta["scheduled"]
            all_rows.extend(lines)
        with (shard / "card_counts.csv").open(newline="", encoding="utf-8") as f:
            for line in csv.DictReader(f):
                key = (line["style"], line["opponent"], line["card"])
                for col in EVENT_FIELDS[3:]:
                    totals[key][col] += int(line[col])
    assert ranges == set(range(0, TOTAL_REPETITIONS, SHARD_SIZE))
    assert len(all_rows) == SCHEDULED
    good = [r for r in all_rows
            if r["completed"] == "True" and r["winner"] and not r["error"]]
    bad = [r for r in all_rows if r not in good]
    matchup = defaultdict(Counter)
    methods = Counter()
    for row in good:
        assert "Pressure Fighter" in (row["seat_a"], row["seat_b"])
        opponent = (row["seat_b"] if row["seat_a"] == "Pressure Fighter"
                    else row["seat_a"])
        matchup[opponent][row["winner"]] += 1
        methods[row["method"]] += 1
    for name in ("Fast Grappler", "The Technician"):
        assert sum(matchup[name].values()) <= 1200
    assert sum(methods.values()) == len(good)
    result = {
        "scheduled": SCHEDULED, "completed": len(good),
        "incomplete": len(bad),
        "matchups": {
            name: {
                "scheduled": 1200,
                "completed": sum(matchup[name].values()),
                "pressure_wins": matchup[name]["Pressure Fighter"],
                "opponent_wins": matchup[name][name],
                "pressure_win_pct": round(
                    100 * matchup[name]["Pressure Fighter"]
                    / max(1, sum(matchup[name].values())), 4),
            }
            for name in ("Fast Grappler", "The Technician")
        },
        "win_methods": dict(methods.most_common()),
        "pressure_fighter_deck": snapshot(),
        "shiko_stomp_plays_by_style": {
            style: sum(t["played_uses"] for (s, opp, card), t in totals.items()
                       if s == style and opp == "ALL" and card == "Shiko Stomp")
            for style in STYLES
        },
        "note": "Pressure Fighter draft40 fixed with copies and YOR-C1; opponents reroll 13 distinct noncore cards every bout. V5.2/B7 AI + PR18 Shiko fix.",
    }
    (output / "summary.json").write_text(json.dumps(result, indent=2))
    with (output / "all_bouts.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=BOUT_FIELDS)
        w.writeheader()
        w.writerows(all_rows)
    with (output / "card_success_rates.csv").open("w", newline="", encoding="utf-8") as fh:
        extra = ["deck_win_pct", "played_win_pct", "plays_per_100_bouts"]
        w = csv.DictWriter(fh, fieldnames=list(EVENT_FIELDS) + extra)
        w.writeheader()
        for key, counts in sorted(totals.items()):
            n = counts["deck_bouts"]
            played = counts["played_bouts"]
            row = {**dict(zip(EVENT_FIELDS[:3], key)),
                   **{name: counts[name] for name in EVENT_FIELDS[3:]},
                   "deck_win_pct": None,
                   "played_win_pct": (round(counts["played_wins"] * 100 / played, 3)
                                      if played else None),
                   "plays_per_100_bouts": (round(counts["played_uses"] * 100 / n, 3)
                                          if n else None)}
            w.writerow(row)
    with (output / "incomplete_bouts.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=BOUT_FIELDS)
        w.writeheader()
        w.writerows(bad)
    (output / "draft40_snapshot.json").write_text(
        DECK_FILE.read_text(encoding="utf-8"))
    md = [
        "# Pressure Fighter fixed 40 vs 27+13 opponents",
        "",
        f"- Completed: **{len(good):,} / {SCHEDULED:,}**; incomplete **{len(bad)}**.",
        "- B7 / V5.2 rules; same 27+13 Fast Grappler and Technician opponent builds.",
        "- Pressure Fighter uses fixed exact 40 physical cards including duplicate Oshi/Tsuki etc.",
        "- Pressure Fighter alone uses **Yorikiri YOR-C1**; opponents retain B7 YOR-C3.",
        "- PR #18 Shiko Stomp registry fix included; no card buffs.",
        "",
        "| Opponent | PF wins | Opponent wins | PF win % |",
        "|---|---:|---:|---:|",
    ]
    for opp, res in result["matchups"].items():
        md.append(f"| {opp} | {res['pressure_wins']:,} | "
                  f"{res['opponent_wins']:,} | {res['pressure_win_pct']:.2f}% |")
    md += ["", "Shiko Stomp played uses by style: "
           + ", ".join(f"{k} = {v}"
                       for k, v in result["shiko_stomp_plays_by_style"].items())]
    (output / "summary.md").write_text("\n".join(md) + "\n")
    print("\n".join(md), flush=True)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=("run", "report"))
    p.add_argument("--start", type=int, default=0)
    p.add_argument("--stop", type=int, default=2)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--root", type=Path)
    args = p.parse_args()
    if args.command == "run":
        assert 0 <= args.start < args.stop <= TOTAL_REPETITIONS
        run(args.start, args.stop, args.output)
    else:
        assert args.root
        report(args.root, args.output)

if __name__ == "__main__":
    main()
