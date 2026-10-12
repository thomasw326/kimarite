"""B5: B4 20 Kimarite with 40-card, top-30-affinity weighted draw piles.

Does not change live catalogue. Installs an isolated in-process R21 card map
before constructing styles, preserving usual affinity under the Kimarite family name.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from itertools import combinations
from pathlib import Path


def install_final22() -> None:
    from . import catalog, style_builds_v5, style_ai_v5, affinity_v5
    from .r21_gauntlet import load_arms
    from .r21_variant_rules import build_variant_card

    roster = json.loads((Path(__file__).resolve().parents[2] / "data/final_22_kimarite_roster.json").read_text())
    assert len(roster["arms"]) == 22 and len(set(roster["arms"])) == 22
    arms = {a.arm_id: a for a in load_arms()}
    assert all(i in arms for i in roster["arms"])
    assert len({arms[i].kimarite for i in roster["arms"]}) == 22
    excluded_families = {"Abisetaoshi", "Kirikaeshi"}
    final_by_family = {arms[i].kimarite: i for i in roster["arms"]
                       if arms[i].kimarite not in excluded_families}
    assert len(final_by_family) == 20
    variant_by_name = {"R21:" + ident: arms[ident].kimarite for ident in roster["arms"]
                       if arms[ident].kimarite not in excluded_families}
    old_affinity = affinity_v5.affinity

    def family_affinity(style: str, name: str) -> int:
        return old_affinity(style, variant_by_name.get(name, name))

    def preferred(cards, style, limit):
        unique = {variant_by_name.get(c.name, c.name): c for c in cards}
        return sorted(unique.values(), key=lambda c: (-family_affinity(style, c.name), c.name))[:limit]

    def least_useful(cards, style, count, protected=()):
        options = [c for c in cards if c.card_id not in set(protected)]
        options.sort(key=lambda c: (family_affinity(style, c.name), c.name, c.card_id))
        return frozenset(c.card_id for c in options[:max(0, count)])

    def convert(cards):
        return tuple(build_variant_card(final_by_family[c.name], card_id=c.card_id)
                     if c.is_kimarite else c for c in cards)

    # Exclude both families from the whole draw pool as well as starting choices.
    # Affinity ranking then promotes the next eligible choices automatically.
    new_pool = convert(c for c in catalog.CARD_POOL
                       if not (c.is_kimarite and c.name in excluded_families))
    new_starting = convert(c for c in catalog.STARTING_KIMARITE
                           if c.name not in excluded_families)
    assert {c.name for c in new_pool if c.is_kimarite} == set(variant_by_name)
    assert len(new_starting) == 20
    assert all(c.name in {x.name for x in new_pool} for c in new_starting)
    assert all(not c.is_kimarite or c.name in set(variant_by_name)
               for c in new_pool)
    assert excluded_families.isdisjoint({c.name for c in new_pool})
    assert {"Driving Force — Power Payoff", "Crushing Pressure — Power Crusher"}.issubset({x.name for x in new_pool})
    assert sum(not x.is_kimarite for x in new_pool) == sum(not x.is_kimarite for x in catalog.CARD_POOL)
    style_builds_v5.B5_WEIGHTED_AFFINITY_DECK = True
    style_builds_v5.CARD_POOL = new_pool
    style_builds_v5.STARTING_KIMARITE = new_starting
    style_builds_v5.preferred = preferred
    style_builds_v5.least_useful = least_useful
    style_ai_v5.card_affinity = family_affinity


def run_batch(start_pair: int, end_pair: int, repetitions: int, seed: int, max_turns: int, output: Path) -> None:
    from .style_simulate_v5 import run_style_bout
    from .styles_v5 import STYLES
    from .models import Side

    install_final22()
    styles = tuple(STYLES)
    assert len(styles) == 15
    pairs = tuple(combinations(styles, 2))
    assert len(pairs) == 105
    assert 0 <= start_pair < end_pair <= len(pairs)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(("pair","repetition","seat_a","seat_b","winner","win_method",
                         "completed","turns","error"))
        for repeat in range(repetitions):
            for pair_index in range(start_pair, end_pair):
                first, second = pairs[pair_index]
                pair_seed = seed + repeat * 10000 + pair_index
                for a, b in ((first,second),(second,first)):
                    result = run_style_bout(a,b,seed=pair_seed,max_turns=max_turns,experimental_final22=True)
                    winner = (a if result.state.winner is Side.A else
                              b if result.state.winner is Side.B else "")
                    writer.writerow((pair_index,repeat,a,b,winner,result.state.win_method or "",
                                     result.completed,result.turns,result.unsupported_reason or ""))
    print(json.dumps({"start_pair":start_pair,"end_pair":end_pair,
                       "repetitions":repetitions,"bouts":(end_pair-start_pair)*2*repetitions,
                       "output":str(output)}))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--start-pair", type=int, required=True)
    parser.add_argument("--end-pair", type=int, required=True)
    parser.add_argument("--repetitions", type=int, default=40)
    parser.add_argument("--seed",type=int,default=20261011)
    parser.add_argument("--max-turns",type=int,default=100)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    run_batch(args.start_pair,args.end_pair,args.repetitions,args.seed,args.max_turns,args.output)

if __name__ == "__main__":
    main()
