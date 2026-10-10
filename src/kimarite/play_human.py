"""Play a basic Kimarite human-vs-AI bout from a terminal.

Usage:
    python -m kimarite.play_human --human Fujinokawa --opponent Fujinokawa

Human Technique/Grip look-and-keep and card-effect choices are interactive.
"""
from __future__ import annotations

import argparse

from .catalog import PLAYTEST_WRESTLERS, CARD_POOL
from .effects import ChoiceRequired, IllegalPlay
from .human_bout import HumanBout
from .models import Side
from .setup import BoutConfig, FighterConfig
from .styles_v5 import STYLES



CARD_DESCRIPTIONS = {
    "oshi": "Exchange: Gain 1 Push, gain 1 Play, then draw 1 card. After play, mill 1 card from the top of your Draw Pile.",
}


def _card_lookup(raw: str) -> bool:
    """Show known card information without changing the bout or consuming a Play."""
    if not raw.startswith("/"):
        return False
    query = raw[1:].strip().casefold()
    card = next((c for c in CARD_POOL if c.name.casefold() == query), None)
    if card is None:
        print(f"Unknown card: {raw[1:]}. Try /oshi.")
        return True
    print(f"\n{card.name} [P{card.power} T{card.technique} S{card.spirit}]")
    print(CARD_DESCRIPTIONS.get(query, "Card effect description not yet available in the terminal. Check the Card Library."))
    return True


def _display(bout: HumanBout) -> None:
    view = bout.view()
    state = bout.state
    print(f"\nTurn {view.turn_number} | Position {view.position:+d} | Momentum {view.momentum:+d}")
    print(f"Power: you {view.own_power} / opponent {view.opponent_power}")
    print(f"Grip: you {view.own_grip} / opponent {view.opponent_grip}")
    print(f"Your plays remaining: {view.plays_remaining}")
    print(f"Your hand: {len(view.hand)} cards | Opponent: {view.opponent_hand_size} cards")
    print("Playable:")
    for action in bout.actions():
        card = action.card
        print(f"  {action.hand_index}: {card.name} [P{card.power} T{card.technique} S{card.spirit}]")
    if state.event_log:
        print("Recent events:")
        for event in state.event_log[-6:]:
            print(f"  {event}")


def _ask_effect_choices(bout: HumanBout, hand_index: int) -> None:
    choices: dict = {}
    while True:
        try:
            bout.play(hand_index, choices=choices)
            return
        except ChoiceRequired as requirement:
            print(f"{requirement.card_name}: choose {requirement.choice_name}")
            for i, option in enumerate(requirement.options):
                print(f"  {i}: {option}")
            while True:
                raw = input("Choice number: ").strip()
                if raw.isdigit() and int(raw) < len(requirement.options):
                    choices[requirement.choice_name] = requirement.options[int(raw)]
                    break
                print("Enter one of the option numbers above.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Play Kimarite against the AI")
    parser.add_argument("--human", default="Fujinokawa", choices=sorted(PLAYTEST_WRESTLERS))
    parser.add_argument("--opponent", default="Fujinokawa", choices=sorted(PLAYTEST_WRESTLERS))
    parser.add_argument("--human-style", choices=sorted(STYLES), help="Use an experimental V5 archetype")
    parser.add_argument("--opponent-style", choices=sorted(STYLES), help="Opposing V5 archetype")
    parser.add_argument("--seed", type=int, default=20261009)
    parser.add_argument("--ai-mode", default="tactical", choices=("tactical", "personality"))
    parser.add_argument("--max-turns", type=int, default=100)
    args = parser.parse_args()
    tachiai_sacrifice = None
    if args.human_style:
        from .style_builds_v5 import build_style
        preview = build_style(args.human_style, seed=args.seed, ranking=1).fighter.wrestler
    else:
        preview = PLAYTEST_WRESTLERS[args.human].build(ranking=1)
    if preview.prepared_tachiai_card.name == "Headlong Charge":
        print(f"Headlong Charge: sacrifice {preview.starting_kimarite.name} for +1 Momentum and +1 Push?")
        tachiai_sacrifice = 0 if input("Sacrifice? [y/N]: ").strip().lower() in {"y", "yes"} else None

    if args.human_style or args.opponent_style:
        if not (args.human_style and args.opponent_style):
            parser.error("Provide both --human-style and --opponent-style.")
        bout = HumanBout.new_styles(
            args.human_style, args.opponent_style,
            seed=args.seed, max_turns=args.max_turns,
            tachiai_sacrifice=tachiai_sacrifice,
        )
    else:
        bout = HumanBout.new(
            BoutConfig(
                FighterConfig(args.human, args.seed, ranking=1),
                FighterConfig(args.opponent, args.seed + 101, ranking=2),
            ),
            human_side=Side.A,
            ai_mode=args.ai_mode,
            max_turns=args.max_turns,
            tachiai_sacrifice=tachiai_sacrifice,
        )

    print("KIMARITE — V5 terminal prototype")
    print("Enter a card number, 'pass', 'quit', or '/oshi' to inspect Oshi.")
    while not bout.finished:
        if bout.pending_selection is not None:
            pending = bout.pending_selection
            print(f"\nLooked at {len(pending.options)} card(s); keep exactly {pending.keep}:")
            for i, card in enumerate(pending.options):
                print(f"  {i}: {card.name} [P{card.power} T{card.technique} S{card.spirit}]")
            raw_selection = input("Indices to keep, separated by spaces (or quit): ").strip()
            if _card_lookup(raw_selection):
                continue
            if raw_selection.lower() in {"quit", "q"}:
                return
            try:
                indices = [int(word) for word in raw_selection.split()]
                bout.choose_cards(indices)
            except (ValueError, IllegalPlay) as exc:
                print(f"Selection invalid: {exc}")
            continue
        _display(bout)
        raw = input("\nAction: ").strip().lower()
        if _card_lookup(raw):
            continue
        if raw in {"quit", "q"}:
            print("Session ended without recording a victory.")
            return
        if raw in {"pass", "p", "end"}:
            bout.end_turn()
            continue
        if not raw.isdigit():
            print("Enter a card index, 'pass', or 'quit'.")
            continue
        index = int(raw)
        try:
            _ask_effect_choices(bout, index)
        except (IllegalPlay, KeyError, ValueError, NotImplementedError) as exc:
            print(f"Action unavailable: {exc}")

    print("\n--- FINAL ---")
    for event in bout.state.event_log[-12:]:
        print(event)
    if bout.state.winner is None:
        print(f"Bout stopped: {bout.stopped_reason}")
    else:
        victor = "You" if bout.state.winner is bout.human_side else "Opponent"
        print(f"{victor} won by {bout.state.win_method}.")


if __name__ == "__main__":
    main()
