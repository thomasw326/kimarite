"""Aggregate verified B7 three-fixed40 mirror shards into readable CSV/JSON."""
import argparse
import csv
import json
from collections import Counter,defaultdict
from pathlib import Path

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=True)
    folders=sorted(x.parent for x in a.input.rglob("manifest.json"))
    assert len(folders)==5,folders
    ranges=set()
    bouts=[]
    cards=defaultdict(Counter)
    for folder in folders:
        m=json.loads((folder/"manifest.json").read_text())
        assert m["completed"]==m["bouts"]==6000 and m["incomplete"]==0,m
        assert m["stop"]-m["start"]==500
        ranges.add((m["start"],m["stop"]))
        with (folder/"bouts.csv").open(newline="",encoding="utf-8") as f:
            bouts.extend(csv.DictReader(f))
        with (folder/"cards.csv").open(newline="",encoding="utf-8") as f:
            for row in csv.DictReader(f):
                key=(row["style"],row["opponent"],row["card"])
                for k,v in row.items():
                    if k not in ("style","opponent","card"):
                        cards[key][k]+=int(v)
    assert ranges=={(i,i+500) for i in range(0,2500,500)},ranges
    assert len(bouts)==30000
    assert all(r["completed"]=="True" and not r["error"] for r in bouts)
    with (a.output/"all_bouts.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=bouts[0]);w.writeheader();w.writerows(bouts)
    grouped=defaultdict(Counter)
    mirrors=defaultdict(Counter)
    methods=Counter()
    for b in bouts:
        key=(b["style_a"],b["style_b"])
        unordered=tuple(sorted(key))
        grouped[unordered]["bouts"]+=1
        grouped[unordered][b["winner_style"]]+=1
        grouped[unordered]["seat_a_wins"]+=int(b["seat_a_won"])
        if b["style_a"]==b["style_b"]:
            mirrors[b["style_a"]]["bouts"]+=1
            mirrors[b["style_a"]]["seat_a_wins"]+=int(b["seat_a_won"])
        methods[(unordered,b["win_method"])]+=1
    assert len(grouped)==6 and all(c["bouts"]==5000 for c in grouped.values())
    assert all(v["bouts"]==5000 for v in mirrors.values()) and len(mirrors)==3
    summary={"total_bouts":30000,"cross_bouts":15000,"mirror_bouts":15000,
             "matchups":[{"styles":list(k),**dict(v)} for k,v in sorted(grouped.items())],
             "mirror_seat_a_win_rates":{k:round(100*v["seat_a_wins"]/v["bouts"],3)
                                        for k,v in sorted(mirrors.items())}}
    (a.output/"summary.json").write_text(json.dumps(summary,indent=2))
    with (a.output/"win_methods.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f);w.writerow(("style_1","style_2","method","wins"))
        for (pair,method),n in sorted(methods.items()):
            w.writerow((*pair,method,n))
    with (a.output/"card_data.csv").open("w",newline="",encoding="utf-8") as f:
        keys=("deck_bouts","deck_copies","deck_wins","played_bouts","played_uses",
              "played_wins","starting_bouts","starting_wins","prepared_bouts",
              "prepared_wins","finisher_wins")
        w=csv.writer(f)
        w.writerow(("style","opponent","card",*keys,"deck_win_pct","played_win_pct"))
        for key,c in sorted(cards.items()):
            w.writerow((*key,*(c[k] for k in keys),
                        round(100*c["deck_wins"]/c["deck_bouts"],3) if c["deck_bouts"] else "",
                        round(100*c["played_wins"]/c["played_bouts"],3) if c["played_bouts"] else ""))
    print(json.dumps(summary,indent=2))

if __name__=="__main__":
    main()
