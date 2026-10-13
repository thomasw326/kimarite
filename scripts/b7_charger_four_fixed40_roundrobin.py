"""B7 15-archetype experimental fixed40 round-robin, including mirrors.

120 unordered matchups (105 cross-style, 15 mirrors), both seats per repetition.
For each repetition run both orientations; mirrors use distinct seeds so each
seat is an independent 40-card shuffle. Both participants count in card metrics.
"""
import argparse
import csv
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

import fast_grappler_draft40_vs_pf40_tt_random13 as previous

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "data/b7_charger_four_fixed40.json"
from kimarite.styles_v5 import STYLES
NAMES = ('Pressure Fighter', 'Fast Grappler', 'The Technician', 'Charger')
PAIRS = tuple((NAMES[i], NAMES[j]) for i in range(len(NAMES)) for j in range(i, len(NAMES)))
BASE_SEED = 2026101309
FIELDS = ("repetition", "pair_index", "style_a", "style_b", "seat_a_won",
          "winner_style", "win_method", "win_source", "completed", "turns", "error",
          "a_starting", "b_starting", "a_prepared", "b_prepared",
          "a_top", "b_top", "a_plays", "b_plays")
COUNT_FIELDS = ("deck_bouts","deck_copies","deck_wins","played_bouts",
                "played_uses","played_wins","starting_bouts","starting_wins",
                "prepared_bouts","prepared_wins","finisher_wins")


def snapshot():
    cfg = json.loads(CONFIG.read_text())
    result = cfg["decks"]
    assert set(result) == set(NAMES)
    for style, counts in result.items():
        assert sum(counts.values()) == 40 and all(v > 0 for v in counts.values())
        assert sum(v for n, v in counts.items() if n in
                   ("Power Water Cantrip",)) == 0
    assert result["Pressure Fighter"]["Yorikiri (YOR-C1)"] == 1
    assert result["The Technician"]["Kirikaeshi"] == 1
    return result


def install():
    from kimarite import style_builds_v5, style_simulate_v5, style_ai_v5
    from kimarite.models import Card, FighterState, Stat, Wrestler
    from kimarite.styles_v5 import STYLES as profiles
    aliases, old_builder = previous.install()
    selected = snapshot()
    catalog = {aliases.get(card.name, card.name):card
               for card in style_builds_v5.CARD_POOL}
    tt = selected["The Technician"]
    assert set(tt) <= set(catalog), sorted(set(tt)-set(catalog))
    assert sum(v for n,v in tt.items() if catalog[n].is_kimarite) == 8
    assert sum(v for n,v in tt.items() if not catalog[n].is_kimarite) == 32
    for style, counts in selected.items():
        assert all(name in catalog or (style == "Pressure Fighter" and name == "Yorikiri (YOR-C1)") for name in counts), style
        assert sum(n for name,n in counts.items() if (catalog[name].is_kimarite if name in catalog else name == "Yorikiri (YOR-C1)")) == 8, style
        assert sum(n for name,n in counts.items() if (not catalog[name].is_kimarite if name in catalog else False)) == 32, style
    assert selected["Fast Grappler"] == previous.fg_snapshot()
    assert selected["Pressure Fighter"] == previous.pf.snapshot()

    def builder(style, seed=0, ranking=1, difficulty=0, *, enable_stat_boosts=False):
        if style in ("Pressure Fighter", "Fast Grappler"):
            return old_builder(style, seed=seed, ranking=ranking,
                               difficulty=difficulty,
                               enable_stat_boosts=enable_stat_boosts)
        assert difficulty == 0 and not enable_stat_boosts
        rng = random.Random(seed)
        current = selected[style]
        templates = [catalog[name] for name, qty in sorted(current.items())
                     for _ in range(qty)]
        physical = [Card(6_000_000+i, c.name,c.power,c.technique,c.spirit,c.is_kimarite)
                    for i,c in enumerate(templates)]
        finishers = sorted((c for c in physical if c.is_kimarite),
                           key=lambda c:(-style_ai_v5.card_affinity(style,c.name),
                                         c.name,c.card_id))
        basics_by_name = {c.name:c for c in physical if not c.is_kimarite}
        basics = sorted(basics_by_name.values(),
                        key=lambda c:(-style_ai_v5.card_affinity(style,c.name),c.name))
        assert len(finishers) == 8 and len(basics) >= 10
        starter = rng.choices(finishers[:3], weights=(3,2,1))[0]
        prepared = rng.choices(basics[:10], weights=tuple(range(10,0,-1)))[0]
        top_candidates = [c for c in basics[:10] if c.name != prepared.name]
        assert len(top_candidates) == 9
        top = rng.choices(top_candidates, weights=tuple(range(9,0,-1)))[0]
        for card in (starter, prepared, top):
            physical.remove(card)
        rng.shuffle(physical)
        p = profiles[style]
        third = next(s for s in Stat if s.value not in {p.primary,p.secondary})
        wrestler = Wrestler(style,*p.stats,starter,prepared,top,
                            primary=Stat(p.primary),secondary=Stat(p.secondary),
                            tertiary=third,ranking=ranking)
        fighter = FighterState(wrestler,draw_pile=[top,*physical],
                               kimarite_zone=[starter])
        fighter.random_selected_names = ()
        inventory = [starter,prepared,*fighter.draw_pile]
        assert len(inventory)==40 and len({c.card_id for c in inventory})==40
        assert Counter(aliases.get(c.name,c.name) for c in inventory)==Counter(current)
        return style_builds_v5.StyleBuild(fighter,frozenset())

    style_builds_v5.build_style = builder
    style_simulate_v5.build_style = builder
    return aliases,builder


def run(start,stop,output):
    from kimarite.models import Side
    from kimarite.style_simulate_v5 import run_style_bout
    aliases,builder=install()
    output.mkdir(parents=True,exist_ok=True)
    stats=defaultdict(Counter)
    errors=[]
    total=0
    with (output/"bouts.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader()
        for rep in range(start,stop):
            for index,(left,right) in enumerate(PAIRS):
                for orientation in range(2):
                    a,b=((left,right) if orientation==0 else (right,left))
                    # Independent seed per orientation, including mirrors.
                    seed=BASE_SEED+rep*10000+index*2+orientation
                    result=run_style_bout(a,b,seed=seed,max_turns=100,
                                          difficulty=0,experimental_final22=True)
                    state=result.state
                    win_side=state.winner
                    winner=(a if win_side is Side.A else b if win_side is Side.B else "")
                    played={side:Counter(aliases.get(name,name)
                            for owner,name in state.card_plays if owner is side)
                            for side in (Side.A,Side.B)}
                    row=dict(repetition=rep,pair_index=index,style_a=a,style_b=b,
                             seat_a_won=int(win_side is Side.A) if winner else "",
                             winner_style=winner,
                             win_method=aliases.get(state.win_method or "",state.win_method or ""),
                             win_source=state.win_source or "",
                             completed=result.completed,turns=result.turns,
                             error=result.unsupported_reason or "",
                             a_starting=aliases.get(state.fighter_a.wrestler.starting_kimarite.name,
                                                    state.fighter_a.wrestler.starting_kimarite.name),
                             b_starting=aliases.get(state.fighter_b.wrestler.starting_kimarite.name,
                                                    state.fighter_b.wrestler.starting_kimarite.name),
                             a_prepared=aliases.get(state.fighter_a.wrestler.prepared_tachiai_card.name,
                                                    state.fighter_a.wrestler.prepared_tachiai_card.name),
                             b_prepared=aliases.get(state.fighter_b.wrestler.prepared_tachiai_card.name,
                                                    state.fighter_b.wrestler.prepared_tachiai_card.name),
                             a_top=aliases.get(state.fighter_a.wrestler.top_of_deck_card.name,
                                               state.fighter_a.wrestler.top_of_deck_card.name),
                             b_top=aliases.get(state.fighter_b.wrestler.top_of_deck_card.name,
                                               state.fighter_b.wrestler.top_of_deck_card.name),
                             a_plays="; ".join(f"{n} x{v}" for n,v in sorted(played[Side.A].items())),
                             b_plays="; ".join(f"{n} x{v}" for n,v in sorted(played[Side.B].items())))
                    w.writerow(row);total+=1
                    if not result.completed or not winner or result.unsupported_reason:
                        errors.append(row)
                        continue
                    for side,style,opponent,seed_side in (
                        (Side.A,a,b,seed),(Side.B,b,a,seed+1009)):
                        initial=builder(style,seed=seed_side,
                                        ranking=1 if side is Side.A else 2).fighter
                        inventory=[initial.wrestler.starting_kimarite,
                                   initial.wrestler.prepared_tachiai_card,
                                   *initial.draw_pile]
                        assert len(inventory)==40 and len({c.card_id for c in inventory})==40
                        counts=Counter(aliases.get(c.name,c.name) for c in inventory)
                        assert counts==Counter(snapshot()[style])
                        won=int(win_side is side)
                        starter=aliases.get(initial.wrestler.starting_kimarite.name,
                                            initial.wrestler.starting_kimarite.name)
                        prepared=aliases.get(initial.wrestler.prepared_tachiai_card.name,
                                             initial.wrestler.prepared_tachiai_card.name)
                        for card,copies in counts.items():
                            for key in ((style,opponent,card),(style,"ALL",card)):
                                counts_row=stats[key]
                                counts_row["deck_bouts"]+=1
                                counts_row["deck_copies"]+=copies
                                counts_row["deck_wins"]+=won
                                if card in played[side]:
                                    counts_row["played_bouts"]+=1
                                    counts_row["played_uses"]+=played[side][card]
                                    counts_row["played_wins"]+=won
                                if card==starter:
                                    counts_row["starting_bouts"]+=1
                                    counts_row["starting_wins"]+=won
                                if card==prepared:
                                    counts_row["prepared_bouts"]+=1
                                    counts_row["prepared_wins"]+=won
                                if won and state.win_source=="kimarite" and row["win_method"]==card:
                                    counts_row["finisher_wins"]+=1
    with (output/"cards.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=("style","opponent","card",*COUNT_FIELDS))
        w.writeheader()
        for key,c in sorted(stats.items()):
            w.writerow(dict(zip(("style","opponent","card"),key)) |
                       {name:c[name] for name in COUNT_FIELDS})
    meta={"start":start,"stop":stop,"bouts":total,"completed":total-len(errors),
          "incomplete":len(errors),"pairs":PAIRS,"mirror_bouts":(stop-start)*6,
          "source":"B7 3 frozen plus 12 experimental style-informed fixed40; V5.2 AI"}
    (output/"manifest.json").write_text(json.dumps(meta,indent=2))
    if errors:
        with (output/"incomplete.json").open("w") as f:
            json.dump(errors,f,indent=2)
        raise RuntimeError(f"{len(errors)} incomplete; first {errors[0]}")
    print(json.dumps(meta),flush=True)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--start",type=int,required=True)
    p.add_argument("--stop",type=int,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    assert 0<=args.start<args.stop<=5000
    run(args.start,args.stop,args.output)


if __name__=="__main__":
    main()
