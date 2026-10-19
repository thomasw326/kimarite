"""Aggregate ten 1000-bout matchups and verify neutral openings for B8 five-deck RR."""
from __future__ import annotations
import argparse
import csv
import json
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

NAMES=("Pressure Fighter","Fast Grappler","The Technician","Charger","Mountain")
PAIRS=tuple(combinations(NAMES,2))
COUNT_FIELDS=("deck_bouts","deck_copies","deck_wins","played_bouts",
              "played_uses","played_wins","starting_bouts","starting_wins",
              "prepared_bouts","prepared_wins","finisher_wins")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    folders=sorted(x.parent for x in args.input.rglob("manifest.json"))
    assert len(folders)==10,(len(folders),folders)
    ranges=set()
    total=0
    bouts=[]
    cards=defaultdict(Counter)
    for folder in folders:
        manifest=json.loads((folder/"manifest.json").read_text())
        assert manifest["bouts"]==manifest["completed"]==1000 and manifest["incomplete"]==0,manifest
        assert manifest["stop"]-manifest["start"]==50
        assert set(tuple(t) for t in manifest["pairs"])==set(PAIRS)
        ranges.add((manifest["start"],manifest["stop"]))
        with (folder/"bouts.csv").open(newline="",encoding="utf-8") as f:
            rows=list(csv.DictReader(f))
            assert len(rows)==1000
            bouts.extend(rows)
        with (folder/"cards.csv").open(newline="",encoding="utf-8") as f:
            for row in csv.DictReader(f):
                key=(row["style"],row["opponent"],row["card"])
                for field in COUNT_FIELDS:
                    cards[key][field]+=int(row[field])
        total+=manifest["bouts"]
    assert ranges=={(i*50,(i+1)*50) for i in range(10)},ranges
    assert total==len(bouts)==10000
    assert all(r["completed"]=="True" and not r["error"] and r["winner_style"] for r in bouts)
    pair=defaultdict(Counter)
    style=defaultdict(Counter)
    kimarite=defaultdict(Counter)
    prepared=defaultdict(Counter)
    first_top=defaultdict(Counter)
    finishes=defaultdict(Counter)
    methods=Counter()
    torinaoshi=0
    seats=defaultdict(Counter)
    for r in bouts:
        k=tuple(sorted((r["style_a"],r["style_b"]),key=NAMES.index))
        assert k in PAIRS
        v=pair[k]
        a,b=r["style_a"],r["style_b"]
        win=r["winner_style"]
        assert win in (a,b)
        v["bouts"]+=1
        v[win]+=1
        v["seat_a_wins"]+=int(r["seat_a_won"])
        seats[k][(a,b)]+=1
        style[a]["bouts"]+=1
        style[b]["bouts"]+=1
        style[win]["wins"]+=1
        torinaoshi+=int(r["torinaoshi"])
        methods[(k[0],k[1],win,r["win_method"],r["win_source"])]+=1
        if r["win_source"]=="kimarite":
            finishes[(win,r["win_method"])]["wins"]+=1
        for side,who in (("a",a),("b",b)):
            is_win=(who==win)
            kimarite[(who,r[side+"_starting"])]["starts"]+=1
            kimarite[(who,r[side+"_starting"])]["wins"]+=int(is_win)
            prepared[(who,r[side+"_prepared"])]["starts"]+=1
            first_top[(who,r[side+"_top"])]["starts"]+=1
    assert set(pair)==set(PAIRS)
    assert all(v["bouts"]==1000 for v in pair.values())
    assert all(seats[k][k]==seats[k][(k[1],k[0])]==500 for k in PAIRS),seats
    assert all(style[n]["bouts"]==4000 for n in NAMES)
    assert all(sum(kimarite[(n,card)]["starts"] for style_name,card in kimarite if style_name==n)==4000 for n in NAMES)
    # Each style can legally start EVERY physical Kimarite copy. Almost surely
    # all distinct finisher names appear after 4000 uniformly random starters.
    for n in NAMES:
        distinct={card for who,card in kimarite if who==n}
        assert len(distinct)>=6,(n,distinct)
    with (args.output/"all_bouts.csv").open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=bouts[0])
        writer.writeheader()
        writer.writerows(bouts)
    with (args.output/"matchups.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f)
        w.writerow(("style_a","style_b","bouts","style_a_wins","style_a_win_pct","style_b_wins","style_b_win_pct","seat_a_wins"))
        for k in PAIRS:
            v=pair[k]
            w.writerow((*k,v["bouts"],v[k[0]],round(100*v[k[0]]/1000,2),v[k[1]],round(100*v[k[1]]/1000,2),v["seat_a_wins"]))
    with (args.output/"starters.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f)
        w.writerow(("style","starting_kimarite","starts","wins","win_pct"))
        for (who,name),v in sorted(kimarite.items()):
            w.writerow((who,name,v["starts"],v["wins"],round(100*v["wins"]/v["starts"],2)))
    with (args.output/"prepared.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f);w.writerow(("style","prepared_tachiai","starts"))
        for (who,name),v in sorted(prepared.items()):
            w.writerow((who,name,v["starts"]))
    with (args.output/"top_cards.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f);w.writerow(("style","starting_top_card","starts"))
        for (who,name),v in sorted(first_top.items()):
            w.writerow((who,name,v["starts"]))
    with (args.output/"finishers.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f);w.writerow(("winner_style","finisher","wins"))
        for (who,card),v in sorted(finishes.items(),key=lambda item:(item[0][0],-item[1]["wins"])):
            w.writerow((who,card,v["wins"]))
    with (args.output/"win_methods.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f);w.writerow(("style_a","style_b","winner","method","source","wins"))
        for names,count in sorted(methods.items()):
            w.writerow((*names,count))
    with (args.output/"card_data.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f);w.writerow(("style","opponent","card",*COUNT_FIELDS,"deck_win_pct","played_win_pct","starting_win_pct"))
        for (who,op,card),v in sorted(cards.items()):
            d=lambda w,n: round(100*v[w]/v[n],3) if v[n] else ""
            w.writerow((who,op,card,*(v[x] for x in COUNT_FIELDS),
                        d("deck_wins","deck_bouts"),d("played_wins","played_bouts"),d("starting_wins","starting_bouts")))
    summary={
        "status":"complete","total_bouts":10000,"distinct_matchups":10,
        "bouts_per_pair":1000,"bouts_per_orientation_per_pair":500,
        "bouts_per_style":4000,"torinaoshi_count":torinaoshi,
        "opening_policy":"uniform physical 8 Kimarite; uniform 2 physical non-Kimarite without replacement; no affinity opening ranks",
        "pairs":[{"style_a":a,"style_b":b,"bouts":1000,
                  "style_a_wins":pair[(a,b)][a],"style_b_wins":pair[(a,b)][b],
                  "style_a_win_pct":round(100*pair[(a,b)][a]/1000,2),
                  "style_b_win_pct":round(100*pair[(a,b)][b]/1000,2)}
                 for a,b in PAIRS],
        "styles":[{"name":n,"bouts":style[n]["bouts"],
                   "wins":style[n]["wins"],"losses":4000-style[n]["wins"],
                   "win_pct":round(style[n]["wins"]/40,2),
                   "distinct_starting_kimarite":len({card for who,card in kimarite if who==n})}
                   for n in NAMES],
    }
    (args.output/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    import os
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:
            f.write("## B8 neutral opening — 5-style round robin, 10,000 bouts\n\n")
            f.write("| Style | Wins | Win rate | Distinct starting Kimarite |\n|---|---:|---:|---:|\n")
            for s in summary["styles"]:
                f.write(f"| {s['name']} | {s['wins']}/4000 | {s['win_pct']:.2f}% | {s['distinct_starting_kimarite']} |\n")
            f.write(f"\nAll ten matchups had 1000 bouts, 500 per seat orientation. Torinaoshi: {torinaoshi}.\n")
    print(json.dumps({"status":"success","bouts":10000,
                      "matchups":10,"styles":summary["styles"]},indent=2),flush=True)

if __name__=="__main__":
    main()
