"""Validate 69 authored decks and run B11 AI-vs-AI round robin with style proxies.

Design caveat: all 69 wrestlers inherit one of 15 AI styles. These are not
69 bespoke validated AIs. The 28+12 authored build represents maximum
duplication; base-28 balance must be evaluated separately.
"""
import argparse
import json
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path
from kimarite.catalog import card_by_name
from kimarite.styles_v5 import STYLES

SOURCE = Path(__file__).resolve().parents[1] / "data" / "b11_69_wrestler_decks.json"
ALIASES = {"Driving Force": "Driving Force — Power Payoff"}


def load_designs(duplicate_count=12):
    if not 0 <= duplicate_count <= 12:
        raise ValueError("duplicate_count must be 0..12")
    data = json.loads(SOURCE.read_text(encoding="utf-8"))["wrestlers"]
    assert len(data) == 69, f"expected 69 wrestlers, got {len(data)}"
    output = {}
    for name, row in data.items():
        base, duplicates = row["base"], row["duplicates"]
        assert len(base) == 28 and len(duplicates) == 12, name
        assert len(set(base)) == 28 and len(set(duplicates)) == 12, name
        assert set(duplicates).issubset(base), name
        normalized_base = [ALIASES.get(x, x) for x in base]
        normalized_extra = [ALIASES.get(x, x) for x in duplicates[:duplicate_count]]
        assert sum(card_by_name(c).is_kimarite for c in normalized_base) == 5, name
        assert sum(card_by_name(c).is_kimarite for c in normalized_extra) <= 3, name
        for card in normalized_base + normalized_extra:
            card_by_name(card)
        style_name = row["style"]
        assert style_name in STYLES, (name, style_name)
        style = STYLES[style_name]
        STYLES[name] = replace(style, name=name)
        output[name] = {
            "stats": dict(zip(("power", "technique", "spirit"), style.stats)),
            "cards": normalized_base + normalized_extra,
        }
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--duplicates", type=int, default=12, choices=range(13))
    parser.add_argument("--bouts", type=int, default=138)
    parser.add_argument("--output-dir", default="artifacts/b11_69")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    decks = load_designs(args.duplicates)
    print(json.dumps({"wrestlers": len(decks), "deck_size": 28 + args.duplicates,
                      "total_slots": sum(len(x["cards"]) for x in decks.values()),
                      "styles": len({json.loads(SOURCE.read_text(encoding="utf-8"))["wrestlers"][n]["style"] for n in decks})}))
    if args.validate_only:
        return
    # Reuse the existing mirrored-pair, seed-stable B9 simulator machinery
    # with the newly imported decks; do not silently use the old B9 roster.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import b9_round_robin as engine
    engine.load_decks = lambda: decks
    sys.argv = [sys.argv[0], "--bouts", str(args.bouts),
                "--output-dir", args.output_dir, "--fail-on-errors"]
    engine.main()


if __name__ == "__main__":
    main()
