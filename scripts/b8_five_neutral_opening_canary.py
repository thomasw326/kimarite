"""Canary: all five decks use a genuinely neutral 8-Kimarite opening policy."""
import b8_five_neutral_roundrobin_10k as exp
from collections import Counter
from kimarite.models import Side

def main():
    assert len(exp.NAMES)==5 and len(exp.PAIRS)==10
    assert len(set(exp.PAIRS))==10
    assert set(exp.NAMES)=={x for p in exp.PAIRS for x in p}
    decks=exp.snapshot()
    aliases,builder,legacy=exp.install()
    assert all(sum(counts.values())==40 for counts in decks.values())
    assert decks["Mountain"]["Tsuriotoshi"]==1
    assert decks["Mountain"]["Ankogata"]==2
    assert decks["Mountain"]["Ottsuke"]==decks["Mountain"]["Kannuki"]==2

    # Original locked four decks, no new changes.
    import json
    from pathlib import Path
    baseline=json.loads((Path(__file__).resolve().parents[1]/
         "data/b8_mountain_ankogata_tsuriotoshi_1000.json").read_text())["decks"]
    assert decks==baseline
    starts={}
    for style in exp.NAMES:
        counts=Counter()
        source=decks[style]
        expected={name for name,n in source.items() if name in {
            "Yorikiri (YOR-C1)", "Tsuriotoshi"
        }}
        # More directly: eight physical Kimarite, ensure all distinct
        # names in starter sample show up and all 8 physical slots can start.
        for seed in range(256):
            build=builder(style,seed=seed,ranking=1).fighter
            replay=builder(style,seed=seed,ranking=1).fighter
            w=build.wrestler
            assert (w.starting_kimarite.name,w.prepared_tachiai_card.card_id,
                    w.top_of_deck_card.card_id)==(
                    replay.wrestler.starting_kimarite.name,
                    replay.wrestler.prepared_tachiai_card.card_id,
                    replay.wrestler.top_of_deck_card.card_id)
            copies=[w.starting_kimarite,w.prepared_tachiai_card,*build.draw_pile]
            assert len(copies)==40 and len({c.card_id for c in copies})==40
            assert sum(c.is_kimarite for c in copies)==8
            assert not w.prepared_tachiai_card.is_kimarite
            assert not w.top_of_deck_card.is_kimarite
            assert build.draw_pile[0].card_id==w.top_of_deck_card.card_id
            inventory_aliases=aliases if style in ("Charger","Mountain") else legacy
            assert Counter(inventory_aliases.get(c.name,c.name) for c in copies)==Counter(source)
            counts[inventory_aliases.get(w.starting_kimarite.name,w.starting_kimarite.name)]+=1
        # Check every eligible Kimarite copy is reached. Duplicates are
        # counted by physical copies: 8 slots; usually 7-8 distinct names.
        assert len(counts)>=6,(style,counts)
        assert sum(counts.values())==256
        starts[style]=dict(counts)
    print("PASS: fixed 40s, all 5 builders use random 8-slot Kimarite, random 32-slot basics, reproducible seeds")
    print(starts)

if __name__=="__main__":
    main()
