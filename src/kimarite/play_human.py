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



CARD_LIBRARY_TEXT = {
  "oshi": {
    "timing": "Tachiai / Exchange",
    "effect": "Tachiai: Reveal top cards, adding each card's printed orbs; continue through Oshi/Tsuki until first other card. Discard revealed cards. Exchange: Gain 1 Push and 1 Play. Draw 1. Then Mill 1."
  },
  "tsuki": {
    "timing": "Tachiai / Exchange",
    "effect": "Tachiai: Same reveal-orb chain as Oshi. Exchange: Reduce one opponent Grip by one level if they have one. Gain 1 Play. Draw 1. Then Mill 1."
  },
  "tsuppari": {
    "timing": "Tachiai / Exchange",
    "effect": "Tachiai: Shuffle 3 Oshi, 3 Tsuki and 3 Shove into your Draw Pile (9 generated cards). Exchange: Gain 1 Momentum; if another Oshi/Tsuki/Tsuppari/Shove was played this turn, gain 1 Push. Gain 1 Play, draw 1, then Mill 1."
  },
  "headlong charge": {
    "timing": "Tachiai / Exchange",
    "effect": "Tachiai / Exchange: You may discard a Kimarite in play; if you do, gain 1 Momentum and 1 Push. Mill 2. Prepared copy is discarded after Tachiai."
  },
  "nodowa": {
    "timing": "Tachiai / Exchange",
    "effect": "Tachiai: Gain 2 Power. Opponent looks at 2 fewer cards when resolving Technique, minimum 2. Exchange: Gain 2 Power. Remove 1 opposing Temporary."
  },
  "harite": {
    "timing": "Tachiai / Exchange",
    "effect": "Gain 1 Power. Opponent loses 1 Power."
  },
  "gain left grip": {
    "timing": "Tachiai / Exchange",
    "effect": "Tachiai: If you win Technique, establish your Left Grip. Exchange: Increase Left Grip by 1 level (max Level 2). Temporary: Prevent the next 1 Push you receive while this protection remains active. Exchange: After resolving the other effects, Recycle 1 (move 1 card from your Discard Pile to the bottom of your Draw Pile)."
  },
  "gain right grip": {
    "timing": "Tachiai / Exchange",
    "effect": "Tachiai: If you win Technique, establish your Right Grip. Exchange: Increase Right Grip by 1 level (max Level 2). Temporary: Prevent the next 1 Push you receive while this protection remains active. Exchange: After resolving the other effects, Recycle 1 (move 1 card from your Discard Pile to the bottom of your Draw Pile)."
  },
  "uwate": {
    "timing": "Tachiai / Exchange",
    "effect": "Exchange: Improve Left Grip by 1. Look at the top X cards of your Draw Pile, where X is your Total Grip. If Left Grip is Deep, play 1 without spending a Play; otherwise, draw 1. Put the rest on the bottom of your Draw Pile. Temporary: Prevent the next 1 Push you receive while this protection remains active. Exchange: After resolving the other effects, Recycle 1 (move 1 card from your Discard Pile to the bottom of your Draw Pile)."
  },
  "shitate": {
    "timing": "Tachiai / Exchange",
    "effect": "Improve Right Grip by 1. If Right Grip is already Deep, gain 2 Push instead. Temporary: Prevent the next 1 Push you receive while this protection remains active. Exchange: After resolving the other effects, Recycle 1 (move 1 card from your Discard Pile to the bottom of your Draw Pile)."
  },
  "attempt two-handed grip": {
    "timing": "Tachiai / Exchange",
    "effect": "Exchange: Establish 1 chosen Grip at Level 1 (without reducing an existing higher Grip). Temporary: Remains until the beginning of your next turn. If it survives, establish both Left and Right Grip at Level 1 (without reducing existing higher Grips). If removed or prevented before then, lose 1 Momentum."
  },
  "attempt deep outside grip": {
    "timing": "Tachiai / Exchange",
    "effect": "Exchange: Establish Left Grip at Level 1 (without reducing an existing higher Grip). Temporary: Remains until the beginning of your next turn. If it survives, set your Left Grip to Deep (2). If removed or prevented before then, lose 1 Momentum."
  },
  "attempt deep inside grip": {
    "timing": "Tachiai / Exchange",
    "effect": "Exchange: Establish Right Grip at Level 1 (without reducing an existing higher Grip). Temporary: Remains until the beginning of your next turn. If it survives, set your Right Grip to Deep (2). If removed or prevented before then, lose 1 Momentum."
  },
  "shiko stomp": {
    "timing": "Tachiai / Exchange",
    "effect": "Tachiai / Exchange: Enter a persistent Temporary. When an opponent effect would negatively affect you or something you control, prevent that effect and discard Shiko Stomp. It does not expire at the beginning of your turn."
  },
  "salt throw": {
    "timing": "Tachiai / Exchange",
    "effect": "Tachiai / Exchange: If your Discard Pile has 7+ cards, return the entire Discard Pile to the bottom of the Draw Pile. Enter a persistent Temporary; at the start of each of your turns, recycle one discarded card to the bottom of your Draw Pile."
  },
  "stare down": {
    "timing": "Tachiai / Exchange",
    "effect": "Tachiai: If you win Power, gain 1 Push. If you win Technique, improve opening card access by 1 kept card. If you win Spirit, gain 1 Momentum. Exchange: Look at top 1 plus the number of Tachiai comparisons won cards; keep 1, bottom the rest."
  },
  "power water": {
    "timing": "Tachiai / Exchange",
    "effect": "Exchange: Shuffle 6 Power Water Cantrip cards into your Draw Pile."
  },
  "belt slap": {
    "timing": "Tachiai / Exchange",
    "effect": "Exchange: Gain 1 Push. If you won Spirit in the Tachiai by 3 or more, gain 1 Momentum."
  },
  "tsuri": {
    "timing": "Tachiai / Exchange",
    "effect": "Exchange: If you have no usable Grip, gain 1 Grip instead; otherwise, gain 1 Power. Temporary: Remains until the beginning of your next turn. If it survives, gain 3 Push if your Power is 5+ and your Total Grip is 2+; otherwise, gain 1 Push."
  },
  "yori": {
    "timing": "Tachiai / Exchange",
    "effect": "Exchange: If you have no usable Grip, gain 1 Grip instead; otherwise, gain 1 Push. Temporary: Remains until the beginning of your next turn. If it survives, gain 3 Momentum if your Total Grip is greater than your opponent's Total Grip; otherwise, gain 1 Momentum."
  },
  "gaburi": {
    "timing": "Tachiai / Exchange",
    "effect": "Exchange: If you have no usable Grip, gain 1 Grip instead; otherwise, gain 1 Momentum. Temporary: Remains until the beginning of your next turn. If it survives and your Power is greater than your opponent's Power, create a Yorikiri in your Kimarite Zone."
  },
  "ottsuke": {
    "timing": "Tachiai / Exchange",
    "effect": "Choose: reduce 1 opposing Grip by 1 level, OR remove opposing Grip-referencing Temporary or Kimarite and gain 1 Momentum. No Push reward."
  },
  "hold position": {
    "timing": "Tachiai / Exchange",
    "effect": "Exchange — Temporary: Your opponent cannot gain Push while Hold Position remains. Remains until the beginning of your next turn. If it survives, gain 1 Momentum and 1 Power."
  },
  "immovable": {
    "timing": "Tachiai / Exchange",
    "effect": "Exchange — Temporary: Gain 1 Power. Remains until the beginning of your next turn. If it survives and your opponent gained no Push while it remained, gain 2 Momentum."
  },
  "henka": {
    "timing": "Tachiai / Exchange",
    "effect": "Tachiai: If your Technique is greater than your opponent's Spirit, the bout begins at Position 0, regardless of Tachiai Push. Exchange: Draw 1 card."
  },
  "pull": {
    "timing": "Tachiai / Exchange",
    "effect": "Exchange — Choose: (1) Lose 1 Momentum and 1 Position; put 1 card from your discard pile on top of your Draw Pile. Temporary: At the start of your next turn, if Pull remains, reverse your Momentum. (2) Draw 1 card, then discard 1 card."
  },
  "get underneath": {
    "timing": "Tachiai / Exchange",
    "effect": "Tachiai / Exchange: Gain 1 Momentum and 1 Push. Opponent searches their deck for a Kimarite and puts it in their Kimarite Zone."
  },
  "read the move": {
    "timing": "Tachiai / Exchange",
    "effect": "Exchange: Choose one — Remove 1 card from your opponent's Temporary Zone. If you do, gain 1 Momentum and draw 1 card; OR draw 1 card."
  },
  "reset to neutral": {
    "timing": "Tachiai / Exchange",
    "effect": "Exchange: Remove all cards from both players' Temporary Zones. Remove all your Grip. If your Momentum is negative, set it to 0. If you removed at least 1 Grip this way, gain 1 Position."
  },
  "regain balance": {
    "timing": "Tachiai / Exchange",
    "effect": "Exchange: Draw 1 card. If your Momentum is negative, gain 2 Momentum and 2 Power."
  },
  "sidestep": {
    "timing": "Tachiai / Exchange",
    "effect": "Tachiai unchanged. Exchange Temporary: Enter Side-by-Side at current distance. While active, ALL Push from both wrestlers is 0. At start of your next turn resolve favorable Position by Momentum, then discard."
  },
  "use the tawara": {
    "timing": "Tachiai / Exchange",
    "effect": "Exchange — Temporary: Lose 1 Position. Gain 1 Momentum. Search for a Kimarite. While this remains, Push cannot move you. At the start of your next turn, discard this. Exchange: After resolving the other effects, Recycle 1 (move 1 card from your Discard Pile to the bottom of your Draw Pile)."
  },
  "kannuki": {
    "timing": "Tachiai / Exchange",
    "effect": "While Kannuki remains, your opponent cannot establish or improve Grip and cannot gain benefits from their existing Grip. At the start of your next turn, reduce both their Left Grip and Right Grip by 1 level, then discard Kannuki."
  },
  "morozashi": {
    "timing": "Tachiai / Exchange",
    "effect": "Requires one Level 1 Grip. Gain other Grip at Level 1; protect Grips while Temporary remains. If it survives to your next turn, gain 1 Push (not Momentum). Exchange: After resolving the other effects, Recycle 1 (move 1 card from your Discard Pile to the bottom of your Draw Pile)."
  },
  "yorikiri": {
    "timing": "Start & End of Turn",
    "effect": "Grip 2+ · Momentum 1+ · Position 2+"
  },
  "oshidashi": {
    "timing": "Start & End of Turn",
    "effect": "Position 2+ · Momentum 1+ · (Power Advantage 1+ OR Tachiai Spirit Advantage 3+)"
  },
  "tsukidashi": {
    "timing": "Start & End of Turn",
    "effect": "Position 2+ · Cards Played This Turn 4+"
  },
  "oshitaoshi": {
    "timing": "Start & End of Turn",
    "effect": "Momentum 1+ · Position 1+ · Power 8+"
  },
  "yoritaoshi": {
    "timing": "Start & End of Turn",
    "effect": "Grip 2+ · Position 2+ · Power Advantage 2+"
  },
  "give ground": {
    "timing": "Tachiai / Exchange",
    "effect": "Tachiai: If you lose Spirit, reduce the Push you receive by 1. Exchange: Lose 1 Position. Gain 1 Momentum and 1 Power. Draw 1 card."
  },
  "uwatenage": {
    "timing": "Start & End of Turn",
    "effect": "Deep Left Grip · Momentum 1+ · Position 0+"
  },
  "hatakikomi": {
    "timing": "Start & End of Turn",
    "effect": "Momentum ≤ −2 · Position 0+ · Power 5+"
  },
  "katasukashi": {
    "timing": "Start & End of Turn",
    "effect": "Win: No active Grip; your Momentum +1 or higher; lost Position during your current Exchange turn."
  },
  "hikiotoshi": {
    "timing": "Start & End of Turn",
    "effect": "Momentum ≤ −2 · Position 0+ · Grip 1+"
  },
  "tottari": {
    "timing": "Start & End of Turn",
    "effect": "No Grip · Opponent's Grip attempt was prevented or reduced during the specified turn window"
  },
  "tsukiotoshi": {
    "timing": "Start & End of Turn",
    "effect": "Gained Momentum this turn · (Position −3 OR Momentum −2)"
  },
  "tsukitaoshi": {
    "timing": "Start & End of Turn",
    "effect": "Momentum 2+ · Cards Played This Turn 4+"
  },
  "tsuridashi": {
    "timing": "Start & End of Turn",
    "effect": "Total Grip 3+ · Position 0+ · Power 5+"
  },
  "kotenage": {
    "timing": "Start & End of Turn",
    "effect": "Opponent has no Grip · Momentum 1+ · 5+ cards remaining in hand"
  },
  "abisetaoshi": {
    "timing": "Start & End of Turn",
    "effect": "Grip 2+ · Momentum 1+ · Power 7+"
  },
  "shove": {
    "timing": "Tachiai / Exchange",
    "effect": "Tachiai: Gain 1 Push; if your Position is +3 after the opening Push, immediately win by Shove. Exchange: Gain 1 Push. If you played Oshi/Tsuki/Tsuppari earlier this turn, draw 1 then discard 1 from hand. Mill 1."
  },
  "explosive step — fumikomi": {
    "timing": "Tachiai / Exchange",
    "effect": "Tachiai: If you win Spirit, gain 1 Push. Exchange: Gain 1 Momentum; if your Momentum was 0 or less before play, gain 1 Push. Mill 2 in both phases."
  },
  "shitatenage": {
    "timing": "Start & End of Turn",
    "effect": "Deep Right Grip · Momentum 1+ · Position 0+"
  }
}

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
    details = CARD_LIBRARY_TEXT.get(query)
    if details:
        print(f"Timing: {details['timing']}")
        print(details["effect"])
    else:
        print(CARD_DESCRIPTIONS.get(query, "Effect text unavailable in the current V5 print pool."))
    return True



def _zone_summary(bout: HumanBout) -> None:
    state = bout.state
    for side, label in ((bout.human_side, "YOUR"), (state.opponent_side(bout.human_side), "OPPONENT")):
        fighter = state.fighter(side)
        temporary = ", ".join(entry.card.name for entry in fighter.temporary_zone) or "(empty)"
        kimarite = ", ".join(card.name for card in fighter.kimarite_zone) or "(empty)"
        print(f"{label} TEMPORARY: {temporary}")
        print(f"{label} KIMARITE: {kimarite}")
    you, them = state.fighter(bout.human_side), state.opponent(bout.human_side)
    print(f"Discard: you {len(you.discard_pile)} / opponent {len(them.discard_pile)}")
    print(f"Draw piles: you {len(you.draw_pile)} / opponent {len(them.draw_pile)}")


def _discard_lookup(raw: str, bout: HumanBout) -> bool:
    if raw != "/discard":
        return False
    state = bout.state
    for side, label in ((bout.human_side, "Your"), (state.opponent_side(bout.human_side), "Opponent")):
        cards = state.fighter(side).discard_pile
        print(f"{label} discard ({len(cards)}): " + (", ".join(card.name for card in cards) or "(empty)"))
    return True


def _public_event(event: str, bout: HumanBout) -> str:
    opponent = bout.state.opponent(bout.human_side).wrestler.name
    if event.startswith(opponent + " draws "):
        return f"{opponent} draws a card."
    return event


def _print_new_events(bout: HumanBout, seen: int) -> int:
    events = bout.state.event_log
    if len(events) > seen:
        print("\n--- EVENTS SINCE LAST DECISION ---")
        for event in events[seen:]:
            print("  " + _public_event(event, bout))
    return len(events)


def _display(bout: HumanBout) -> None:
    view = bout.view()
    state = bout.state
    print(f"\nTurn {view.turn_number} | Position {view.position:+d} | Momentum {view.momentum:+d}")
    print(f"Power: you {view.own_power} / opponent {view.opponent_power}")
    print(f"Grip: you {view.own_grip} / opponent {view.opponent_grip}")
    print(f"Your plays remaining: {view.plays_remaining}")
    print(f"Your hand: {len(view.hand)} cards | Opponent: {view.opponent_hand_size} cards")
    _zone_summary(bout)
    print("Playable:")
    for action in bout.actions():
        card = action.card
        print(f"  {action.hand_index}: {card.name} [P{card.power} T{card.technique} S{card.spirit}]")
    if state.event_log:
        print("Recent events:")
        for event in state.event_log[-6:]:
            print("  " + _public_event(event, bout))


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
    if args.human_style and args.opponent_style:
        from .style_builds_v5 import build_style
        from .catalog import CARD_POOL
        for style_name, style_seed in ((args.human_style, args.seed), (args.opponent_style, args.seed + 1009)):
            build = build_style(style_name, seed=style_seed, ranking=1)
            excluded = [card.name for card in CARD_POOL if card.card_id in build.excluded_ids]
            print(f"{style_name} excluded ({len(excluded)}): " + (", ".join(excluded) or "(none)"))
        print("Note: current V5 exclusion ranking is under review; these are actual exclusions.")
    print("Enter card number, pass, quit, /cardname, or /discard.")
    seen_events = 0
    while not bout.finished:
        if bout.pending_selection is not None:
            seen_events = _print_new_events(bout, seen_events)
            _zone_summary(bout)
            pending = bout.pending_selection
            if len(pending.options) == pending.keep:
                print(f"Automatically keeping all {pending.keep} revealed card(s).")
                bout.choose_cards(list(range(pending.keep)))
                continue
            hand = bout.state.fighter(bout.human_side).hand
            print("Current hand: " + (", ".join(c.name for c in hand) or "(empty)"))
            print(f"\nLooked at {len(pending.options)} card(s); keep exactly {pending.keep}:")
            for i, card in enumerate(pending.options):
                print(f"  {i}: {card.name} [P{card.power} T{card.technique} S{card.spirit}]")
            raw_selection = input("Indices to keep, separated by spaces (or quit): ").strip()
            if _discard_lookup(raw_selection.lower(), bout) or _card_lookup(raw_selection):
                continue
            if raw_selection.lower() in {"quit", "q"}:
                return
            try:
                indices = [int(word) for word in raw_selection.split()]
                bout.choose_cards(indices)
            except (ValueError, IllegalPlay) as exc:
                print(f"Selection invalid: {exc}")
            continue
        seen_events = _print_new_events(bout, seen_events)
        _display(bout)
        raw = input("\nAction: ").strip().lower()
        if _discard_lookup(raw, bout) or _card_lookup(raw):
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
