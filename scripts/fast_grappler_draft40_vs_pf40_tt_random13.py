"""Fast Grappler round-2 fixed 40 vs PF fixed 40 and Technician 27+13.

Mirrored difficulty-0 V5.2/B7 comparison: 2,400 scheduled bouts.
Reuses the successful PF draft40 installer, shared V5.2 AI, corrected final22,
and Technician fresh 27+13 sampler. No rules, affinity, or deck changes.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

import pressure_fighter_draft40_vs_random13 as pf

ROOT = Path(__file__).resolve().parents[1]
FG_FILE = ROOT / "data/fast_grappler_draft40_20261012.json"
PF_FILE = ROOT / "data/pressure_fighter_draft40_20261012.json"
STYLES = ("Fast Grappler", "Pressure Fighter", "The Technician")
PAIRS = (("Fast Grappler", "Pressure Fighter"),
         ("Fast Grappler", "The Technician"))
BASE_SEED = 20261014
TOTAL_REPETITIONS = 600
SHARD_SIZE = 150
SCHEDULED = TOTAL_REPETITIONS * len(PAIRS) * 2

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
    "starting_kimarite_bouts", "starting_kimarite_wins",
    "prepared_tachiai_bouts", "prepared_tachiai_wins",
    "random_bouts", "random_played_bouts",
)


def fg_snapshot():
    data = json.loads(FG_FILE.read_text(encoding="utf-8"))
    counts = data["copy_count"]
    assert data["wrestler"] == "Fast Grappler"
    assert len(counts) == 31 and sum(counts.values()) == 40
    assert counts["Yorikiri"] == 2
    assert all(type(n) is int and n > 0 for n in counts.values())
    assert sum(counts[n] for n in (
        "Yorikiri", "Uwatedashinage", "Shitatenage", "Oshidashi",
        "Uwatenage", "Hikiotoshi", "Tsukiotoshi"
    )) == 8
    assert "Tsukidashi" not in counts and "Tsukitaoshi" not in counts
    assert "Power Water Cantrip" not in counts
    return counts


def install():
    from kimarite import style_ai_v5, style_builds_v5, style_simulate_v5
    from kimarite.models import Card, FighterState, Stat, Wrestler
    from kimarite.styles_v5 import STYLES as profiles

    # Installs FINAL22, PF-only Yorikiri C1, and real 27+13 Technician builder.
    aliases, old_builder = pf.install()
    selected = fg_snapshot()
    catalogue = {
        aliases.get(card.name, card.name): card
        for card in style_builds_v5.CARD_POOL
    }
    assert len(catalogue) == len(style_builds_v5.CARD_POOL)
    assert set(selected) <= set(catalogue), sorted(set(selected) - set(catalogue))
    assert catalogue["Yorikiri"].name == "R21:R21-YOR-C3"
    assert sum(v for n, v in selected.items() if catalogue[n].is_kimarite) == 8
    assert sum(v for n, v in selected.items() if not catalogue[n].is_kimarite) == 32

    def builder(style, seed=0, ranking=1, difficulty=0, *,
                enable_stat_boosts=False):
        if style != "Fast Grappler":
            return old_builder(
                style, seed=seed, ranking=ranking, difficulty=difficulty,
                enable_stat_boosts=enable_stat_boosts,
            )
        assert difficulty == 0 and not enable_stat_boosts
        rng = random.Random(seed)
        templates = [
            catalogue[name]
            for name, count in sorted(selected.items())
            for _ in range(count)
        ]
        assert len(templates) == 40
        physical = [
            Card(5_000_000 + index, c.name, c.power, c.technique, c.spirit,
                 c.is_kimarite)
            for index, c in enumerate(templates)
        ]

        # Physical duplicates count: both Yorikiri copies are eligible to be
        # the opening finisher. Weight openings using the existing 3:2:1
        # ranked selection, exactly as in the PF fixed-40 runner.
        kimarite = sorted(
            (c for c in physical if c.is_kimarite),
            key=lambda c: (-style_ai_v5.card_affinity(style, c.name),
                           c.name, c.card_id),
        )
        basics_by_name = {
            c.name: c for c in physical if not c.is_kimarite
        }
        basics = sorted(
            basics_by_name.values(),
            key=lambda c: (-style_ai_v5.card_affinity(style, c.name), c.name),
        )
        assert len(kimarite) == 8 and len(basics) >= 10
        starter = rng.choices(kimarite[:3], weights=(3, 2, 1))[0]
        prepared = rng.choices(
            basics[:10], weights=tuple(range(10, 0, -1))
        )[0]
        top_candidates = [c for c in basics[:10] if c.name != prepared.name]
        assert len(top_candidates) == 9
        top = rng.choices(
            top_candidates, weights=tuple(range(9, 0, -1))
        )[0]
        for picked in (starter, prepared, top):
            physical.remove(picked)
        rng.shuffle(physical)

        profile = profiles[style]
        third = next(
            st for st in Stat
            if st.value not in {profile.primary, profile.secondary}
        )
        wrestler = Wrestler(
            style, *profile.stats, starter, prepared, top,
            primary=Stat(profile.primary), secondary=Stat(profile.secondary),
            tertiary=third, ranking=ranking,
        )
        fighter = FighterState(
            wrestler, draw_pile=[top, *physical], kimarite_zone=[starter]
        )
        fighter.random_selected_names = ()
        inventory = [starter, prepared, *fighter.draw_pile]
        assert len(inventory) == 40
        assert len({c.card_id for c in inventory}) == 40
        actual = Counter(aliases.get(c.name, c.name) for c in inventory)
        assert actual == Counter(selected), (actual, selected)
        return style_builds_v5.StyleBuild(fighter, frozenset())

    style_builds_v5.build_style = builder
    style_simulate_v5.build_style = builder
    return aliases, builder


def canonical(name, aliases):
    return aliases.get(name, name)


def _record_stats(stats, style, opponent, copies, random_names, plays, state,
                  side, aliases, starter, prepared):
    won = int(state.winner is side)
    for name, count in copies.items():
        for key in ((style, opponent, name), (style, "ALL", name)):
            c = stats[key]
            c["deck_bouts"] += 1
            c["deck_copies"] += count
            if name in plays:
                c["played_bouts"] += 1
                c["played_uses"] += plays[name]
                c["played_wins"] += won
                if name in random_names:
                    c["random_played_bouts"] += 1
            if name in random_names:
                c["random_bouts"] += 1
            if name == starter:
                c["starting_kimarite_bouts"] += 1
                c["starting_kimarite_wins"] += won
            if name == prepared:
                c["prepared_tachiai_bouts"] += 1
                c["prepared_tachiai_wins"] += won
            if (won and state.win_source == "kimarite"
                    and canonical(state.win_method, aliases) == name):
                c["finisher_wins"] += 1


def run(start, stop, output):
    from kimarite.models import Side
    from kimarite.style_simulate_v5 import run_style_bout

    aliases, builder = install()
    output.mkdir(parents=True, exist_ok=True)
    stats = defaultdict(Counter)
    rows = []
    failures = []
    for rep in range(start, stop):
        for pair_index, (first, second) in enumerate(PAIRS):
            seed = BASE_SEED + rep * 10000 + pair_index
            for a, b in ((first, second), (second, first)):
                result = run_style_bout(
                    a, b, seed=seed, max_turns=100,
                    difficulty=0, experimental_final22=True,
                )
                state = result.state
                winner = (
                    a if state.winner is Side.A
                    else b if state.winner is Side.B else ""
                )
                rebuilt = {
                    Side.A: builder(a, seed=seed, ranking=1).fighter,
                    Side.B: builder(b, seed=seed + 1009, ranking=2).fighter,
                }
                inventories = {}
                for side, style in ((Side.A, a), (Side.B, b)):
                    live, initial = state.fighter(side), rebuilt[side]
                    for field in (
                        "starting_kimarite", "prepared_tachiai_card",
                        "top_of_deck_card",
                    ):
                        assert getattr(live.wrestler, field).name == getattr(
                            initial.wrestler, field
                        ).name
                    inv = [
                        initial.wrestler.starting_kimarite,
                        initial.wrestler.prepared_tachiai_card,
                        *initial.draw_pile,
                    ]
                    assert len(inv) == 40 and len({c.card_id for c in inv}) == 40
                    copies = Counter(canonical(x.name, aliases) for x in inv)
                    random_names = tuple(initial.random_selected_names)
                    if style == "Fast Grappler":
                        assert copies == Counter(fg_snapshot())
                        assert random_names == ()
                    elif style == "Pressure Fighter":
                        assert copies == Counter(pf.snapshot())
                        assert random_names == ()
                    else:
                        assert style == "The Technician"
                        assert all(n == 1 for n in copies.values())
                        assert len(set(random_names)) == 13
                        assert len(random_names) == 13
                        assert set(random_names) <= set(copies)
                    inventories[side] = (copies, random_names)

                a_plays = Counter(
                    canonical(name, aliases) for side, name in state.card_plays
                    if side is Side.A
                )
                b_plays = Counter(
                    canonical(name, aliases) for side, name in state.card_plays
                    if side is Side.B
                )
                record = {
                    "repetition": rep, "pair_index": pair_index,
                    "seat_a": a, "seat_b": b, "seed": seed,
                    "completed": result.completed, "winner": winner,
                    "method": canonical(state.win_method or "", aliases),
                    "source": state.win_source or "", "turns": result.turns,
                    "error": result.unsupported_reason or "",
                    "a_starting_kimarite": canonical(
                        state.fighter_a.wrestler.starting_kimarite.name, aliases
                    ),
                    "b_starting_kimarite": canonical(
                        state.fighter_b.wrestler.starting_kimarite.name, aliases
                    ),
                    "a_prepared_tachiai": canonical(
                        state.fighter_a.wrestler.prepared_tachiai_card.name, aliases
                    ),
                    "b_prepared_tachiai": canonical(
                        state.fighter_b.wrestler.prepared_tachiai_card.name, aliases
                    ),
                    "a_top_deck": canonical(
                        state.fighter_a.wrestler.top_of_deck_card.name, aliases
                    ),
                    "b_top_deck": canonical(
                        state.fighter_b.wrestler.top_of_deck_card.name, aliases
                    ),
                    "a_random13": "; ".join(inventories[Side.A][1]),
                    "b_random13": "; ".join(inventories[Side.B][1]),
                    "a_cards_played": "; ".join(
                        f"{n} x{count}" for n, count in sorted(a_plays.items())
                    ),
                    "b_cards_played": "; ".join(
                        f"{n} x{count}" for n, count in sorted(b_plays.items())
                    ),
                }
                rows.append(record)
                if not result.completed or not winner or result.unsupported_reason:
                    failures.append(record)
                    continue
                for side, style, opp, plays in (
                    (Side.A, a, b, a_plays),
                    (Side.B, b, a, b_plays),
                ):
                    inv, random_names = inventories[side]
                    f = state.fighter(side)
                    _record_stats(
                        stats, style, opp, inv, random_names, plays, state, side,
                        aliases,
                        canonical(f.wrestler.starting_kimarite.name, aliases),
                        canonical(f.wrestler.prepared_tachiai_card.name, aliases),
                    )
    assert len(rows) == (stop - start) * len(PAIRS) * 2
    with (output / "bouts.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=BOUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    with (output / "card_counts.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=EVENT_FIELDS)
        writer.writeheader()
        for key, counts in sorted(stats.items()):
            writer.writerow({
                **dict(zip(EVENT_FIELDS[:3], key)),
                **{k: counts[k] for k in EVENT_FIELDS[3:]},
            })
    manifest = {
        "range": [start, stop],
        "scheduled": len(rows),
        "completed": len(rows) - len(failures),
        "incomplete": len(failures),
        "fixed_fast_grappler_40": fg_snapshot(),
        "fixed_pressure_fighter_40": pf.snapshot(),
        "technician": "curated 27 + 13 fresh distinct from noncore pool per bout",
        "fast_grappler_yorikiri": "R21:YOR-C3; two physical copies",
        "pressure_fighter_yorikiri": "R21:YOR-C1; one physical copy",
        "rules": "B7/V5.2, corrected UWD M2 and UWA M2 predicates",
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "range": manifest["range"], "scheduled": manifest["scheduled"],
        "completed": manifest["completed"],
        "incomplete": manifest["incomplete"],
    }), flush=True)


def report(root, output):
    output.mkdir(parents=True, exist_ok=True)
    shards = sorted(
        d for d in root.iterdir() if d.is_dir()
        and (d / "manifest.json").exists()
    )
    assert len(shards) == TOTAL_REPETITIONS // SHARD_SIZE
    ranges, all_rows = set(), []
    total = defaultdict(Counter)
    for shard in shards:
        manifest = json.loads((shard / "manifest.json").read_text())
        start, stop = manifest["range"]
        assert stop - start == SHARD_SIZE and start not in ranges
        ranges.add(start)
        assert manifest["scheduled"] == SHARD_SIZE * len(PAIRS) * 2
        assert manifest["fixed_fast_grappler_40"] == fg_snapshot()
        assert manifest["fixed_pressure_fighter_40"] == pf.snapshot()
        with (shard / "bouts.csv").open(newline="", encoding="utf-8") as f:
            values = list(csv.DictReader(f))
        assert len(values) == manifest["scheduled"]
        all_rows.extend(values)
        with (shard / "card_counts.csv").open(
            newline="", encoding="utf-8"
        ) as f:
            for row in csv.DictReader(f):
                key = (row["style"], row["opponent"], row["card"])
                for name in EVENT_FIELDS[3:]:
                    total[key][name] += int(row[name])
    assert ranges == set(range(0, TOTAL_REPETITIONS, SHARD_SIZE))
    assert len(all_rows) == SCHEDULED
    good = [
        r for r in all_rows
        if r["completed"] == "True" and r["winner"] and not r["error"]
    ]
    bad = [
        r for r in all_rows
        if r["completed"] != "True" or not r["winner"] or r["error"]
    ]
    assert len(good) + len(bad) == SCHEDULED
    if bad:
        print(f"WARNING: {len(bad)} unfinished bouts; see incomplete_bouts.csv")
    summary_match = defaultdict(Counter)
    by_seat = defaultdict(Counter)
    winners_by_method = defaultdict(Counter)
    for row in good:
        assert "Fast Grappler" in (row["seat_a"], row["seat_b"])
        opp = (
            row["seat_b"] if row["seat_a"] == "Fast Grappler"
            else row["seat_a"]
        )
        summary_match[opp][row["winner"]] += 1
        by_seat[(opp, "A" if row["seat_a"] == "Fast Grappler" else "B")][
            row["winner"]
        ] += 1
        winners_by_method[(row["winner"], opp)][row["method"]] += 1

    result = {
        "scheduled": SCHEDULED,
        "completed": len(good),
        "incomplete": len(bad),
        "fast_grappler_deck": fg_snapshot(),
        "pressure_fighter_deck": pf.snapshot(),
        "matchups": {},
        "by_seat": {},
        "fast_grappler_win_methods": {},
        "fast_grappler_opening_kimarite": {},
        "technician_random_card_samples": {},
    }
    for opp in ("Pressure Fighter", "The Technician"):
        outcome = summary_match[opp]
        n = sum(outcome.values())
        assert n + sum(
            1 for r in bad if opp in (r["seat_a"], r["seat_b"])
        ) == 1200
        result["matchups"][opp] = {
            "scheduled": 1200, "completed": n,
            "fast_grappler_wins": outcome["Fast Grappler"],
            "opponent_wins": outcome[opp],
            "fast_grappler_win_pct": round(
                100 * outcome["Fast Grappler"] / n, 3
            ) if n else None,
        }
        for seat in ("A", "B"):
            x = by_seat[(opp, seat)]
            played = sum(x.values())
            result["by_seat"][f"{opp} / FG seat {seat}"] = {
                "completed": played,
                "fg_wins": x["Fast Grappler"],
                "fg_win_pct": round(100 * x["Fast Grappler"]/played, 3)
                if played else None,
            }
        result["fast_grappler_win_methods"][opp] = dict(
            winners_by_method[("Fast Grappler", opp)].most_common()
        )
    for (style, opp, card), v in sorted(total.items()):
        if style == "Fast Grappler" and opp == "ALL" and v[
            "starting_kimarite_bouts"
        ]:
            result["fast_grappler_opening_kimarite"][card] = {
                "bouts": v["starting_kimarite_bouts"],
                "wins": v["starting_kimarite_wins"],
            }

    samples = set()
    for row in good:
        if row["seat_a"] == "The Technician":
            sample = tuple(row["a_random13"].split("; "))
        elif row["seat_b"] == "The Technician":
            sample = tuple(row["b_random13"].split("; "))
        else:
            continue
        assert len(sample) == len(set(sample)) == 13
        samples.add(sample)
    result["technician_random_card_samples"] = {
        "distinct_13_card_sets": len(samples),
        "technician_bouts": 1200 - sum(
            1 for r in bad if "The Technician" in
            (r["seat_a"], r["seat_b"])
        ),
    }

    with (output / "all_bouts.csv").open(
        "w", newline="", encoding="utf-8"
    ) as f:
        w = csv.DictWriter(f, fieldnames=BOUT_FIELDS)
        w.writeheader()
        w.writerows(all_rows)
    with (output / "card_success_rates.csv").open(
        "w", newline="", encoding="utf-8"
    ) as f:
        fields = [*EVENT_FIELDS, "played_win_pct", "plays_per_100_bouts"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for key, v in sorted(total.items()):
            n, played = v["deck_bouts"], v["played_bouts"]
            w.writerow({
                **dict(zip(EVENT_FIELDS[:3], key)),
                **{name: v[name] for name in EVENT_FIELDS[3:]},
                "played_win_pct": round(
                    100 * v["played_wins"] / played, 3
                ) if played else "",
                "plays_per_100_bouts": round(
                    100 * v["played_uses"] / n, 3
                ) if n else "",
            })
    with (output / "incomplete_bouts.csv").open(
        "w", newline="", encoding="utf-8"
    ) as f:
        w = csv.DictWriter(f, fieldnames=BOUT_FIELDS)
        w.writeheader()
        w.writerows(bad)
    (output / "summary.json").write_text(
        json.dumps(result, indent=2)+"\n", encoding="utf-8"
    )
    (output / "fast_grappler_snapshot.json").write_text(
        FG_FILE.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (output / "pressure_fighter_snapshot.json").write_text(
        PF_FILE.read_text(encoding="utf-8"), encoding="utf-8"
    )
    md = [
        "# Fast Grappler updated fixed 40 (round 2) versus PF fixed 40 and Technician 27+13",
        "",
        f"- **Completed: {len(good):,}/{SCHEDULED:,}; "
        f"incomplete: {len(bad)}.**",
        "- B7/V5.2 rules, approved stricter UWD and UWA throw requirements.",
        "- Both fixed decks have 40 physical cards; FG has 2 Yorikiri C3.",
        "- Pressure Fighter retains its approved 40 including Yorikiri C1.",
        "- Technician independently rerolls 13 legal noncore names per build.",
        "",
        "| Opponent | FG wins | Opponent wins | FG win % |",
        "|---|---:|---:|---:|",
    ]
    for opp, x in result["matchups"].items():
        md.append(
            f"| {opp} | {x['fast_grappler_wins']:,} | "
            f"{x['opponent_wins']:,} | "
            f"{x['fast_grappler_win_pct']:.2f}% |"
        )
    md += ["", "## Fast Grappler finishing methods", ""]
    for opp, wins in result["fast_grappler_win_methods"].items():
        md.extend([f"### Versus {opp}", ""])
        md.extend(f"- {method}: {n}" for method, n in wins.items())
        md.append("")
    md += ["## Fast Grappler starting Kimarite", ""]
    for card, v in sorted(
        result["fast_grappler_opening_kimarite"].items(),
        key=lambda kv: -kv[1]["bouts"],
    ):
        md.append(f"- {card}: {v['bouts']} starts; {v['wins']} wins")
    md.append("")
    md.append(
        "Technician distinct 13-card samples: "
        + str(result["technician_random_card_samples"][
            "distinct_13_card_sets"
        ])
    )
    (output / "summary.md").write_text("\n".join(md)+"\n", encoding="utf-8")
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
