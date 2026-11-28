"""Standalone Mountain evolution pilot; no game or roster changes."""
import argparse
import csv
import json
import random
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from b12_60_big_test import (load_designs, run_one, source_checksum, AVAILABLE,
    GENERATED_ONLY, MIN_KIMARITE, MAX_KIMARITE, card_by_name)

def legal(d):
    b, u = d["base"], d["duplicates"]
    return (len(b)==len(set(b))==28 and len(u)==len(set(u))==12
        and set(u)<=set(b) and d["starting_kimarite"] in b
        and MIN_KIMARITE<=sum(card_by_name(c).is_kimarite for c in b)<=MAX_KIMARITE
        and sum(not card_by_name(c).is_kimarite for c in b)>=2)

def key(d):
    return (d["starting_kimarite"], tuple(sorted(d["base"])), tuple(sorted(d["duplicates"])))

def mutate(parent, rng, pool, weights):
    for _ in range(1000):
        b, u = list(parent["base"]), list(parent["duplicates"])
        t=rng.random()
        kind="base" if t<.6 else "duplicate" if t<.9 else "multi"
        if kind=="duplicate":
            old=rng.choice(u)
            opts=sorted(set(b)-set(u))
            u[u.index(old)]=rng.choices(opts, [weights[c] for c in opts])[0]
        else:
            count=1 if kind=="base" else rng.randint(2,3)
            olds=rng.sample([c for c in b if c!=parent["starting_kimarite"]], count)
            opts=sorted(set(pool)-set(b))
            for old in olds:
                new=rng.choices(opts,[weights[c] for c in opts])[0]
                opts.remove(new)
                b[b.index(old)]=new
                if old in u: u[u.index(old)]=new
        d={**parent,"base":b,"duplicates":u,"cards":b+u}
        if legal(d) and key(d)!=key(parent): return d,kind
    raise RuntimeError("No legal mutation")

def evaluate(task):
    d, roster, seed, repeats, limit = task
    wins=Counter(); methods=Counter(); plays=Counter()
    # Stable unique candidate seed identity, independent of its lineage.
    candidate={**d,"id":"candidate","name":"Mountain candidate"}
    for i,opp in enumerate(roster):
        for rep in range(repeats):
            for side in ("A","B"):
                entries=[candidate,opp] if side=="A" else [opp,candidate]
                r=run_one(entries,0,1,seed,i,rep,limit,"max40")
                if r["error"] or r["winner_side"] is None:
                    raise RuntimeError(f"Bout failure: {d['id']} vs {opp['id']}: {r['error']}")
                if r["winner_side"]==side:
                    wins[opp["style_proxy"]]+=1
                    methods[str(r["win_method"])]+=1
                plays.update(p["card"] for p in r["fighters"][side]["plays"])
    n=len(roster)*repeats*2
    return {"wins":sum(wins.values()),"bouts":n,"win_rate":sum(wins.values())/n,
            "wins_by_style":dict(wins),"win_methods":dict(methods),"plays":dict(plays)}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--generations",type=int,default=8)
    p.add_argument("--mutations",type=int,default=16)
    p.add_argument("--workers",type=int,default=2)
    p.add_argument("--seed",type=int,default=20261128)
    p.add_argument("--validation-repeats",type=int,default=10)
    p.add_argument("--smoke",action="store_true")
    p.add_argument("--output",default="artifacts/mountain_evolution")
    args=p.parse_args()
    roster=load_designs("max40")
    originals=[d for d in roster if d["style_proxy"]=="Mountain"]
    assert len(originals)==4
    pool=sorted(set(AVAILABLE)-set(GENERATED_ONLY))
    weights={c:1+sum(c in d["base"] for d in originals)+sum(c in d["duplicates"] for d in originals) for c in pool}
    rng=random.Random(args.seed)
    parents=originals[:]
    seen={key(d) for d in parents}
    out=Path(args.output); out.mkdir(parents=True,exist_ok=True)
    (out/"affinities.json").write_text(json.dumps(weights,indent=2))
    log=[]
    opponents=roster[:4] if args.smoke else roster
    generations=1 if args.smoke else args.generations
    mutations=2 if args.smoke else args.mutations
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        for gen in range(1,generations+1):
            children=[]; metadata={}
            for i in range(mutations):
                parent=parents[i%len(parents)]
                for attempt in range(1000):
                    d,kind=mutate(parent,rng,pool,weights)
                    if key(d) not in seen: break
                else: raise RuntimeError("Unique mutation exhausted")
                seen.add(key(d))
                d={**d,"id":f"G{gen:02d}-{i+1:02d}"}
                children.append(d)
                metadata[d["id"]]=(parent,kind)
            candidates=parents+children
            # New common seed every generation; independent validation below.
            scores=list(ex.map(evaluate,[(d,opponents,args.seed+gen,1,100) for d in candidates]))
            results=dict(zip([d["id"] for d in candidates],scores))
            selected=sorted(candidates,key=lambda d:(-results[d["id"]]["wins"],d["id"]))[:4]
            for d in candidates:
                row={"generation":gen,"deck_id":d["id"],"selected":d in selected,**results[d["id"]]}
                if d["id"] in metadata:
                    parent,kind=metadata[d["id"]]
                    row.update(parent=parent["id"],kind=kind,parent_win_rate=results[parent["id"]]["win_rate"],
                        delta=results[d["id"]]["win_rate"]-results[parent["id"]]["win_rate"],
                        added=sorted(set(d["base"])-set(parent["base"])),
                        removed=sorted(set(parent["base"])-set(d["base"])),
                        duplicates_added=sorted(set(d["duplicates"])-set(parent["duplicates"])),
                        duplicates_removed=sorted(set(parent["duplicates"])-set(d["duplicates"])))
                log.append(row)
            parents=selected
            (out/"screening.json").write_text(json.dumps(log,indent=2))
            (out/"finalists.json").write_text(json.dumps(parents,indent=2))
            print(f"Generation {gen}: "+", ".join(f"{d['id']} {results[d['id']]['win_rate']:.1%}" for d in parents),flush=True)
        validation=list({key(d):d for d in originals+parents}.values())
        scores=list(ex.map(evaluate,[(d,opponents,args.seed+100000,1 if args.smoke else args.validation_repeats,100) for d in validation]))
    (out/"validation.json").write_text(json.dumps({"source_sha256":source_checksum(),"seed":args.seed,"smoke":args.smoke,"results":[{"deck":d,**s} for d,s in zip(validation,scores)]},indent=2))
    rows=[r for r in log if "parent" in r]
    cols=["generation","deck_id","parent","kind","selected","wins","bouts","win_rate","parent_win_rate","delta","added","removed","duplicates_added","duplicates_removed"]
    with (out/"mutations.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=cols,extrasaction="ignore");w.writeheader();w.writerows(rows)
    print("Completed",flush=True)

if __name__=="__main__":
    main()
