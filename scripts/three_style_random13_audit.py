"""V5.2 trio: 27 guaranteed names + 13 independently random names, per bout.

Rules: B7/R26 final 22, style_ai_v5 and affinity unchanged. Only deck
construction is varied; do not interpret it as a V6 opening experiment.
The new player-facing commit/retain Tachiai rules are NOT implemented here.
"""
from __future__ import annotations

import argparse
import csv
import inspect
import json
import random
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

STYLES = ("Pressure Fighter", "Fast Grappler", "The Technician")
PAIRS = tuple(combinations(STYLES, 2))
BASE_SEED = 20261012
CARD_COUNT_FIELDS = (
    "deck_bouts", "deck_wins", "deck_copies",
    "core_bouts", "core_wins", "random_bouts", "random_wins",
    "random_played_bouts", "random_played_wins",
    "first_exchange_hand_bouts", "first_exchange_hand_wins",
    "starting_kimarite_bouts", "starting_kimarite_wins",
    "prepared_tachiai_bouts", "prepared_tachiai_wins",
    "top_deck_bouts", "top_deck_wins",
    "played_bouts", "played_wins", "played_uses", "finisher_wins",
)
BOUT_FIELDS = (
    "repetition", "pair_index", "seat_a", "seat_b", "seed", "winner",
    "win_method", "win_source", "completed", "turns", "error",
    "a_starting_kimarite", "b_starting_kimarite",
    "a_prepared_tachiai", "b_prepared_tachiai",
    "a_top_deck", "b_top_deck",
    "a_random_cards", "b_random_cards",
)
CARD_KEY_FIELDS = ("style", "opponent", "card")
CARD_FIELDS = CARD_KEY_FIELDS + CARD_COUNT_FIELDS


def install():
    from kimarite import style_ai_v5, style_builds_v5, style_simulate_v5
    from kimarite.r26_style_final22 import install_final22
    from kimarite.styles_v5 import STYLES as FULL_STYLES

    install_final22()
    assert len(FULL_STYLES) == 15
    assert set(STYLES).issubset(FULL_STYLES)
    assert style_builds_v5.B6_FIXED_COMPOSITION_DECK
    assert "card_affinity(style, candidate.card.name)" in inspect.getsource(
        style_ai_v5.choose_style_play
    )
    # R26 patches in family-normalized affinity including Pressure Fighter's
    # Power Water adjustment; make sure it is present.
    assert style_ai_v5.card_affinity("Pressure Fighter", "Power Water") != 0
    from kimarite.r21_gauntlet import load_arms
    names = {("R21:" + arm.arm_id): arm.kimarite for arm in load_arms()}
    names["Explosive Step"] = "Explosive Step — Fumikomi"
    from kimarite.models import Card, FighterState, Wrestler, Stat

    source = json.loads((Path(__file__).resolve().parents[1] /
                         "data/three_style_curated_27.json").read_text(encoding="utf-8"))
    core = {
        style: frozenset(names.get(name, name) for name in source["cards"][style])
        for style in STYLES
    }
    # Freeze and validate the user's 27-card lists once per process.
    assert all(len(source["cards"][style]) == 27 and len(core[style]) == 27
               for style in STYLES)
    full = {}
    for card in style_builds_v5.CARD_POOL:
        key = names.get(card.name, card.name)
        assert key not in full, ("Duplicate selectable catalog name", key)
        full[key] = card
    assert len(full) >= 40
    assert all(group <= set(full) for group in core.values())
    assert all("Power Water Cantrip" not in group for group in core.values())
    assert all(len(set(full) - group) >= 13 for group in core.values())

    def curated_27_plus_random_13(style, seed=0, ranking=1, difficulty=0,
                                   *, enable_stat_boosts=False):
        assert style in core
        assert difficulty == 0 and not enable_stat_boosts
        rng = random.Random(seed)
        # Crucial: sample anew from the entire *remaining* legal final-22
        # catalog on EVERY build; no fixed 13-card secondary pool.
        remaining = sorted(set(full) - core[style])
        random_names = rng.sample(remaining, 13)
        selected_names = list(sorted(core[style])) + random_names
        assert len(selected_names) == 40 and len(set(selected_names)) == 40
        source_cards = [full[name] for name in selected_names]
        kimarite_choices = style_builds_v5.preferred(
            [c for c in source_cards if c.is_kimarite], style, 3)
        basic_choices = style_builds_v5.preferred(
            [c for c in source_cards if not c.is_kimarite], style, 10)
        assert len(kimarite_choices) == 3 and len(basic_choices) == 10
        starter_name = rng.choices(kimarite_choices, weights=(3, 2, 1))[0].name
        prepared_name = rng.choices(
            basic_choices, weights=tuple(range(10, 0, -1)))[0].name
        top_candidates = [c for c in basic_choices if c.name != prepared_name]
        assert len(top_candidates) == 9
        top_name = rng.choices(
            top_candidates, weights=tuple(range(9, 0, -1)))[0].name
        physical = [
            Card(3_000_000 + i * 10, c.name, c.power, c.technique, c.spirit, c.is_kimarite)
            for i, c in enumerate(source_cards)
        ]
        def pop_name(name):
            return next(c for c in physical if c.name == name)
        starter = pop_name(starter_name)
        prepared = pop_name(prepared_name)
        top = pop_name(top_name)
        for used in (starter, prepared, top):
            physical.remove(used)
        rng.shuffle(physical)
        profile = FULL_STYLES[style]
        third = next((st for st in Stat
                      if st.value not in {profile.primary, profile.secondary}),
                     Stat(profile.primary))
        wrestler = Wrestler(
            style, *profile.stats, starter, prepared, top,
            primary=Stat(profile.primary), secondary=Stat(profile.secondary),
            tertiary=third, ranking=ranking,
        )
        fighter = FighterState(
            wrestler, draw_pile=[top, *physical], kimarite_zone=[starter])
        fighter.random_selected_names = tuple(sorted(random_names))
        return style_builds_v5.StyleBuild(fighter, frozenset())

    style_builds_v5.build_style = curated_27_plus_random_13
    style_simulate_v5.build_style = curated_27_plus_random_13
    return names


def canonical(name, alias):
    return alias.get(name, name)


def add_metric(stats, style, opponent, card, field, amount):
    for key in ((style, opponent, card), (style, "ALL", card), ("ALL", "ALL", card)):
        stats[key][field] += amount


def mark_event(stats, style, opponent, card, prefix, won, occurrences=1):
    add_metric(stats, style, opponent, card, prefix + "_bouts", 1)
    add_metric(stats, style, opponent, card, prefix + "_wins", won)
    if prefix == "played":
        add_metric(stats, style, opponent, card, "played_uses", occurrences)


def run_shard(start, stop, output):
    from kimarite.models import Side
    from kimarite.style_simulate_v5 import run_style_bout
    from kimarite.styles_v5 import STYLES as FULL_STYLES

    alias = install()
    from kimarite import style_builds_v5
    catalog_names = sorted({
        canonical(c.name, alias)
        for c in (*style_builds_v5.CARD_POOL, *style_builds_v5.STARTING_KIMARITE)
    })
    assert len(PAIRS) == 3
    assert len(catalog_names) >= 50
    assert all(FULL_STYLES[s].stats == {
        "Pressure Fighter": (3, 0, 3),
        "Fast Grappler": (0, 2, 4),
        "The Technician": (2, 4, 0),
    }[s] for s in STYLES)

    output.mkdir(parents=True, exist_ok=True)
    stats = defaultdict(Counter)
    failures = []
    count = 0
    bout_path = output / "bouts.csv"
    with bout_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=BOUT_FIELDS)
        writer.writeheader()
        for repetition in range(start, stop):
            for pair_index, (first, second) in enumerate(PAIRS):
                pair_seed = BASE_SEED + repetition * 10000 + pair_index
                for a, b in ((first, second), (second, first)):
                    result = run_style_bout(
                        a, b, seed=pair_seed, max_turns=100,
                        difficulty=0, experimental_final22=True,
                    )
                    state = result.state
                    winner = (a if state.winner is Side.A else
                              b if state.winner is Side.B else "")
                    row = {
                        "repetition": repetition,
                        "pair_index": pair_index,
                        "seat_a": a, "seat_b": b, "seed": pair_seed,
                        "winner": winner,
                        "win_method": canonical(state.win_method or "", alias),
                        "win_source": state.win_source or "",
                        "completed": str(result.completed),
                        "turns": result.turns,
                        "error": result.unsupported_reason or "",
                        "a_starting_kimarite": canonical(
                            state.fighter_a.wrestler.starting_kimarite.name, alias),
                        "b_starting_kimarite": canonical(
                            state.fighter_b.wrestler.starting_kimarite.name, alias),
                        "a_prepared_tachiai": canonical(
                            state.fighter_a.wrestler.prepared_tachiai_card.name, alias),
                        "b_prepared_tachiai": canonical(
                            state.fighter_b.wrestler.prepared_tachiai_card.name, alias),
                        "a_top_deck": canonical(
                            state.fighter_a.wrestler.top_of_deck_card.name, alias),
                        "b_top_deck": canonical(
                            state.fighter_b.wrestler.top_of_deck_card.name, alias),
                        "a_random_cards": "; ".join(state.fighter_a.random_selected_names),
                        "b_random_cards": "; ".join(state.fighter_b.random_selected_names),
                    }
                    writer.writerow(row)
                    count += 1
                    if not result.completed:
                        failures.append(row)
                        continue

                    for side, style, opponent in ((Side.A, a, b), (Side.B, b, a)):
                        won = int(state.winner is side)
                        fighter = state.fighter(side)
                        # Reconstruct the INITIAL inventory using exactly the
                        # same seeded builder as run_style_bout. Observational;
                        # this does not change the simulated bout.
                        initial = style_builds_v5.build_style(
                            style, seed=(pair_seed if side is Side.A else pair_seed + 1009),
                            ranking=(1 if side is Side.A else 2), difficulty=0,
                        ).fighter
                        iw, fw = initial.wrestler, fighter.wrestler
                        for attr in ("starting_kimarite", "prepared_tachiai_card",
                                     "top_of_deck_card"):
                            assert getattr(iw, attr).card_id == getattr(fw, attr).card_id
                        inventory = [
                            iw.starting_kimarite, iw.prepared_tachiai_card,
                            *initial.draw_pile,
                        ]
                        assert len(inventory) == 40, (style, len(inventory))
                        assert len({c.card_id for c in inventory}) == 40
                        assert len({canonical(c.name, alias) for c in inventory}) == 40
                        pool = Counter(canonical(c.name, alias) for c in inventory)
                        all_random = set(initial.random_selected_names)
                        assert len(all_random) == 13
                        assert set(pool) & all_random == all_random
                        assert all(copies == 1 for copies in pool.values())
                        assert len(set(pool) - all_random) == 27
                        for card, copies in pool.items():
                            mark_event(stats, style, opponent, card, "deck", won)
                            mark_event(stats, style, opponent, card,
                                       "random" if card in all_random else "core", won)
                            add_metric(stats, style, opponent, card, "deck_copies", copies)

                        first_hand = {
                            canonical(n, alias)
                            for n in state.first_exchange_hands.get(side, ())
                        }
                        for card in first_hand:
                            mark_event(stats, style, opponent, card, "first_exchange_hand", won)

                        for attr, prefix in (
                            ("starting_kimarite", "starting_kimarite"),
                            ("prepared_tachiai_card", "prepared_tachiai"),
                            ("top_of_deck_card", "top_deck"),
                        ):
                            card = canonical(getattr(iw, attr).name, alias)
                            mark_event(stats, style, opponent, card, prefix, won)

                        played = Counter(
                            canonical(card, alias)
                            for owner, card in state.card_plays if owner is side
                        )
                        for card, plays in played.items():
                            mark_event(stats, style, opponent, card, "played", won, plays)
                            if card in all_random:
                                mark_event(stats, style, opponent, card,
                                           "random_played", won)

                        if won and state.win_source == "kimarite":
                            finish = canonical(state.win_method or "", alias)
                            assert finish, row
                            add_metric(stats, style, opponent, finish, "finisher_wins", 1)

                    if count % 1000 == 0:
                        print(f"Completed {count} bouts in shard", flush=True)

    metrics_path = output / "card_counts.csv"
    # Every eligible card receives a row, including cards never drawn or played.
    all_cards = sorted(set(catalog_names) | {key[2] for key in stats})
    keys = (
        [(style, opponent, card)
         for style in STYLES
         for opponent in STYLES if opponent != style
         for card in all_cards]
        + [(style, "ALL", card) for style in STYLES for card in all_cards]
        + [("ALL", "ALL", card) for card in all_cards]
    )
    with metrics_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=CARD_FIELDS)
        writer.writeheader()
        for key in keys:
            writer.writerow({
                **dict(zip(CARD_KEY_FIELDS, key)),
                **{f: stats[key][f] for f in CARD_COUNT_FIELDS},
            })

    manifest = {
        "shard": f"{start}-{stop}", "bouts": count,
        "completed": count - len(failures), "errors": len(failures),
        "roster": STYLES, "pairs": PAIRS,
        "seed": BASE_SEED, "repetitions": stop - start,
        "rules": "B7/R26 final 22; 27 curated unique + 13 independent random from full remaining pool per wrestler per bout",
        "not_new_tachiai_rules": True,
        "fixed_core": 27,
        "per_bout_random": 13,
        "random_reselection": "every wrestler, every bout; without replacement",
        "catalog_card_names": len(catalog_names),
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2), flush=True)
    if failures:
        print(f"INCOMPLETE BOUTS ({len(failures)}): {failures[:3]}", flush=True)


def pct(numerator, denominator):
    return round(100 * numerator / denominator, 3) if denominator else ""


def report(root, output, expected):
    alias = install()
    output.mkdir(parents=True, exist_ok=True)
    shard_dirs = sorted(p for p in root.iterdir() if p.is_dir() and (p / "manifest.json").exists())
    assert len(shard_dirs) == expected // 6000, shard_dirs
    repetition_ranges = set()
    all_bouts = []
    cards = defaultdict(Counter)
    for directory in shard_dirs:
        meta = json.loads((directory / "manifest.json").read_text())
        a, b = map(int, meta["shard"].split("-"))
        assert a not in repetition_ranges
        repetition_ranges.add(a)
        assert b - a == 1000 and meta["bouts"] == 6000
        assert meta["completed"] + meta["errors"] == 6000
        assert meta["fixed_core"] == 27 and meta["per_bout_random"] == 13
        with (directory / "bouts.csv").open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 6000
        all_bouts.extend(rows)
        with (directory / "card_counts.csv").open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                key = tuple(row[x] for x in CARD_KEY_FIELDS)
                for field in CARD_COUNT_FIELDS:
                    cards[key][field] += int(row[field])
    assert repetition_ranges == set(range(0, expected // 6, 1000)), repetition_ranges
    assert len(all_bouts) == expected
    valid = [r for r in all_bouts if r["completed"] == "True" and not r["error"] and r["winner"]]
    incomplete = [r for r in all_bouts if r not in valid]
    assert len(valid) + len(incomplete) == expected
    assert all(r["winner"] in (r["seat_a"],r["seat_b"]) for r in valid)

    played = Counter()
    wins = Counter()
    matches = Counter()
    wins_vs = Counter()
    finishes = Counter()
    for row in valid:
        a, b, winner = row["seat_a"], row["seat_b"], row["winner"]
        played[a] += 1
        played[b] += 1
        wins[winner] += 1
        pair = tuple(sorted((a, b)))
        matches[pair] += 1
        wins_vs[(winner, pair)] += 1
        finishes[row["win_method"]] += 1
    assert sum(played.values()) == 2 * len(valid)
    assert sum(matches.values()) == len(valid)
    assert all(matches[tuple(sorted(pair))] <= expected // 3 for pair in PAIRS)

    catalog = sorted({key[2] for key in cards})
    # Output detailed counts and descriptive observational rates.
    output_cards = output / "card_success_rates.csv"
    extra_fields = (
        "deck_win_pct", "core_win_pct", "random_win_pct", "random_played_win_pct",
        "random_played_pct_when_included", "first_exchange_hand_win_pct",
        "starting_kimarite_win_pct", "prepared_tachiai_win_pct",
        "top_deck_win_pct", "played_win_pct",
        "played_bouts_per_100_deck_bouts",
        "finisher_wins_per_100_deck_bouts",
    )
    with output_cards.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CARD_FIELDS + extra_fields)
        writer.writeheader()
        keys = (
            [(style, opponent, card)
             for style in STYLES for opponent in STYLES if opponent != style
             for card in catalog]
            + [(style, "ALL", card) for style in STYLES for card in catalog]
            + [("ALL", "ALL", card) for card in catalog]
        )
        for key in keys:
            data = cards[key]
            x = {k: data[k] for k in CARD_COUNT_FIELDS}
            for event in (
                "deck", "core", "random", "random_played",
                "first_exchange_hand", "starting_kimarite",
                "prepared_tachiai", "top_deck", "played",
            ):
                x[event + "_win_pct"] = pct(
                    data[event + "_wins"], data[event + "_bouts"]
                )
            x["random_played_pct_when_included"] = pct(
                data["random_played_bouts"], data["random_bouts"])
            x["played_bouts_per_100_deck_bouts"] = pct(
                data["played_bouts"], data["deck_bouts"])
            x["finisher_wins_per_100_deck_bouts"] = pct(
                data["finisher_wins"], data["deck_bouts"])
            writer.writerow({**dict(zip(CARD_KEY_FIELDS, key)), **x})

    merged_bouts = output / "all_bouts.csv"
    with merged_bouts.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=BOUT_FIELDS)
        writer.writeheader()
        writer.writerows(all_bouts)

    (output / "incomplete_bouts.csv").write_text("") if not incomplete else None
    if incomplete:
        with (output / "incomplete_bouts.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=BOUT_FIELDS)
            writer.writeheader()
            writer.writerows(incomplete)
    result = {
        "source": "B7/R26 commit c9d3d21c8ccbb7d880fd3265507d56a3ab94ceaa",
        "rules": "V5.2 B7 22 Kimarite; curated 27 unique core + 13 independently rerandomized unique legal cards per wrestler per bout",
        "new_tachiai_commit_retain_rules": False,
        "fixed_core": 27, "per_bout_random": 13,
        "completed": len(valid), "incomplete": len(incomplete),
        "bouts": expected,
        "repetitions_per_pair": expected // 6,
        "bouts_per_pair": expected // 3,
        "bouts_per_style": expected * 2 // 3,
        "card_names_covered": len(catalog),
        "style_results": {
            s: {"wins": wins[s], "bouts": played[s],
                "win_pct": pct(wins[s], played[s])}
            for s in STYLES
        },
        "matchups": [
            {"a": a, "b": b, "bouts": matches[tuple(sorted((a, b)))],
             "a_wins": wins_vs[(a, tuple(sorted((a, b))))],
             "b_wins": wins_vs[(b, tuple(sorted((a, b))))],
             "a_win_pct": pct(wins_vs[(a, tuple(sorted((a, b))))],
                              matches[tuple(sorted((a, b)))])}
            for a, b in PAIRS
        ],
        "win_methods": dict(finishes),
        "files": ["summary.json", "summary.md", "card_success_rates.csv", "all_bouts.csv", "incomplete_bouts.csv"],
    }
    (output / "summary.json").write_text(json.dumps(result, indent=2))
    lines = [
        "# V5.2 trio: 27 curated + 13 random cards (rerolled per wrestler per bout)",
        f"{len(valid):,} completed of {expected:,} scheduled bouts; 3 pairings of 10,000 scheduled bouts.",
        "",
        "## Wrestlers",
        "| Style | Wins | Bouts | Win rate |",
        "|---|---:|---:|---:|",
    ]
    for name, x in result["style_results"].items():
        lines.append(f'| {name} | {x["wins"]:,} | {x["bouts"]:,} | {x["win_pct"]:.2f}% |')
    lines += [
        "", "## Pairwise outcomes",
        "| A | B | A wins | B wins | A win rate |",
        "|---|---|---:|---:|---:|",
    ]
    for x in result["matchups"]:
        lines.append(
            f'| {x["a"]} | {x["b"]} | {x["a_wins"]:,} | {x["b_wins"]:,} | {x["a_win_pct"]:.2f}% |'
        )
    lines += [
        "", "## Card analytics definitions",
        "- See card_success_rates.csv: one row per style/opponent/card, style overall, and pooled total.",
        "- deck_bouts: completed wrestler bouts where at least one physical copy was in the actual 40-card build.",
        "- core_bouts and random_bouts are mutually exclusive per wrestler/card; 27 curated plus 13 sampled from ALL remaining legal names for each bout.",
        "- random_played_bouts: completed bouts where a sampled random card was actually played during Exchange.",
        "- random_played_win_pct: P(win | sampled random card was played); observational, not causal.",
        "- a_random_cards and b_random_cards in all_bouts.csv record all 13 selections for each side of every scheduled bout.",
        "- deck_copies: physical copies summed across those wrestler bouts.",
        "- first_exchange_hand_bouts: card observed in the recorded first Exchange hand (not every later draw).",
        "- starting_kimarite_bouts: card assigned as an opening Kimarite in the Kimarite Zone.",
        "- prepared_tachiai_bouts: card committed as the preselected Tachiai card in the old engine.",
        "- top_deck_bouts: card placed on top of the opening draw pile.",
        "- played_bouts: card was played at least once during Exchange; played_uses counts repeat plays.",
        "- finisher_wins: bouts won by that Kimarite, regardless of whether it was an Exchange card play.",
        "- played_win_pct is P(wrestler wins | card was played), NOT chance its effect succeeds or causal impact.",
        "- Blank percentage means no qualifying observations; card rows with zero exposure are kept.",
        "- These tests use CURRENT B7 rules, not the proposed three-card commit/retain Tachiai rules.",
        "- This is a within-trio ranking only; do not compare its win rates as if they were 15-style results.",
        f"- Any 100-turn-limit exceptions are kept in incomplete_bouts.csv and excluded from win-rate denominators.",
    ]
    (output / "summary.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(result, indent=2), flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=("run", "report"))
    p.add_argument("--start", type=int, default=0)
    p.add_argument("--stop", type=int, default=1)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--root", type=Path)
    p.add_argument("--expected", type=int, default=30000)
    args = p.parse_args()
    if args.command == "run":
        assert 0 <= args.start < args.stop <= 5000
        run_shard(args.start, args.stop, args.output)
    else:
        assert args.root is not None
        report(args.root, args.output, args.expected)


if __name__ == "__main__":
    main()
