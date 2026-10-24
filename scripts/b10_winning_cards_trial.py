"""26 opponents x 30 bouts: unthemed top-performing-card deck on the frozen baseline."""
import argparse, csv, json, sys
from collections import Counter
from pathlib import Path
from dataclasses import replace
sys.path.insert(0, str(Path(__file__).resolve().parent))
import b9_round_robin as rr
from kimarite.catalog import card_by_name

EXCLUDE = {"Attrition Fighter", "Disruptor", "Gripless Fighter", "Stability Master"}
DECK_FILE = Path(__file__).resolve().parent.parent / "data" / "b10_winner_cards_deck.json"

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--start-index", type=int, default=0)
    p.add_argument("--bouts", type=int, default=780)
    p.add_argument("--output-dir", required=True)
    a = p.parse_args()
    baseline = rr.load_decks()
    names = [name for name in baseline if name not in EXCLUDE]
    assert len(names) == 26
    new = json.loads(DECK_FILE.read_text())
    target = new["name"]
    assert target not in baseline
    assert len(new["cards"]) == 40 and sum(card_by_name(c).is_kimarite for c in new["cards"]) == 8
    from collections import Counter as C
    assert len(set(new["cards"])) == 30 and max(C(new["cards"]).values()) == 2
    rr.STYLES[target] = replace(rr.STYLES["The Specialist"], name=target)
    baseline[target] = {"stats":new["stats"],"cards":new["cards"]}
    out=Path(a.output_dir)
    out.mkdir(parents=True,exist_ok=True)
    stats=Counter()
    opponent_wins=Counter()
    methods=Counter()
    errors=Counter()
    with (out/"bouts.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f)
        w.writerow(["index","opponent","first","second","winner","method","turns","error"])
        for index in range(a.start_index,a.start_index+a.bouts):
            opponent=names[(index//30)%26]
            first,second=(target,opponent) if index%2==0 else (opponent,target)
            winner,method,turns,error,state,decks=rr.run_one(first,second,baseline,20261021+index,100)
            w.writerow([index,opponent,first,second,winner,method,turns,error])
            stats["completed"]+=1
            stats["wins" if winner==target else "losses"]+=int(bool(winner))
            if winner==opponent: opponent_wins[opponent]+=1
            if winner==target: methods[method]+=1
            if error: errors[error]+=1
    payload={"source_commit":"311dec7de8a0e3ef30365eeb8f0b8cd832912a4f","roster":26,"bouts":stats["completed"],"wins":stats["wins"],"losses":stats["losses"],"opponent_wins":dict(opponent_wins),"win_methods":dict(methods),"errors":dict(errors),"start_index":a.start_index}
    (out/"summary.json").write_text(json.dumps(payload,indent=2)+"\n")
    print(json.dumps(payload,indent=2))
    if errors or stats["completed"]!=a.bouts or stats["wins"]+stats["losses"]!=a.bouts:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
