from __future__ import annotations

from collections.abc import Iterable

from .models import Card, FighterState, Wrestler


def ai_rank_cards(cards: Iterable[Card], wrestler: Wrestler) -> list[Card]:
    """Rank looked-at cards by Primary, Secondary, then earlier reveal order."""
    indexed = list(enumerate(cards))
    indexed.sort(
        key=lambda item: (
            -item[1].orbs(wrestler.primary),
            -item[1].orbs(wrestler.secondary),
            item[0],
        )
    )
    return [card for _, card in indexed]


def ai_choose_from_look(cards: list[Card], wrestler: Wrestler, keep: int) -> list[Card]:
    if keep < 0:
        raise ValueError("keep must be non-negative")
    return ai_rank_cards(cards, wrestler)[: min(keep, len(cards))]


def look_from_top(fighter: FighterState, count: int) -> list[Card]:
    if count < 0:
        raise ValueError("count must be non-negative")
    return list(fighter.draw_pile[:count])


def keep_and_bottom(
    fighter: FighterState,
    looked: list[Card],
    kept: list[Card],
) -> None:
    if len(looked) > len(fighter.draw_pile):
        raise ValueError("looked cards exceed draw pile")
    if fighter.draw_pile[: len(looked)] != looked:
        raise ValueError("looked cards must be the current top of the draw pile")

    remaining = list(looked)
    for card in kept:
        try:
            remaining.remove(card)
        except ValueError as exc:
            raise ValueError("kept card was not in looked cards") from exc

    fighter.draw_pile = fighter.draw_pile[len(looked) :]
    fighter.hand.extend(kept)
    fighter.draw_pile.extend(remaining)


def ai_look_keep(fighter: FighterState, look: int, keep: int) -> list[Card]:
    looked = look_from_top(fighter, look)
    kept = ai_choose_from_look(looked, fighter.wrestler, keep)
    keep_and_bottom(fighter, looked, kept)
    return kept


def situational_look_keep(state, side, look: int, keep: int) -> list[Card]:
    """Experimental state-aware selection for Technique-primary wrestlers only."""
    from .models import Stat
    from .rules import effective_total_grip
    fighter = state.fighter(side)
    if fighter.wrestler.primary is not Stat.TECHNIQUE:
        return ai_look_keep(fighter, look, keep)
    seen = look_from_top(fighter, look)
    own_position = state.position * state.sign(side)
    own_momentum = state.momentum * state.sign(side)
    urgency = max(0, -own_position) + max(0, -own_momentum)
    grip = effective_total_grip(state, side)
    opponent = state.opponent(side)
    threats = len(opponent.temporary_zone)
    opposing_grip = effective_total_grip(state, state.opponent_side(side))
    grip_starters = {"Gain Left Grip", "Gain Right Grip", "Uwate", "Shitate",
                     "Attempt Two-Handed Grip", "Attempt Deep Outside Grip",
                     "Attempt Deep Inside Grip", "Morozashi"}
    def value(card: Card) -> float:
        name = card.name
        result = card.technique * 2.0 + card.orbs(fighter.wrestler.secondary) * 0.6
        if not grip and name in grip_starters:
            result += 5.0
        if grip and name in {"Yori", "Gaburi", "Tsuri", "Morozashi"}:
            result += 6.0
        if name == "Oshi":
            result += 3.0 + urgency * 2.5
        if name == "Tsuppari":
            result += 1.5 + urgency * 1.8
        if name in {"Read the Move", "Nodowa"} and threats:
            result += min(5, threats * 3)
        if name == "Ottsuke" and (opposing_grip or threats or opponent.kimarite_zone):
            result += 3.0
        if name in {"Regain Balance", "Use the Tawara", "Hold Position"} and urgency >= 2:
            result += urgency * 1.5
        if name == "Reset to Neutral" and urgency >= 3:
            result += 4.0
        return result
    indexed = list(enumerate(seen))
    indexed.sort(key=lambda entry: (-value(entry[1]), entry[0]))
    chosen = [card for _, card in indexed[:keep]]
    keep_and_bottom(fighter, seen, chosen)
    return chosen
