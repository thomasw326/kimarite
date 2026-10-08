from __future__ import annotations

from dataclasses import dataclass

from .catalog import CARD_POOL, ORIGINAL_WRESTLERS
from .models import Card


UNIVERSALLY_PROTECTED_IDS = frozenset({1, 2, 3, 4})


POWER_COMPARISON = frozenset({
    "Tsuppari", "Stare Down", "Hold Position", "Immovable",
    "Oshidashi", "Yoritaoshi",
})
SPIRIT_COMPARISON = frozenset({"Salt Throw", "Stare Down", "Belt Slap", "Henka"})
POWER_THRESHOLD = frozenset({
    "Henka", "Oshitaoshi", "Hatakikomi", "Tsuridashi", "Abisetaoshi",
})
REQUIRES_GRIP = frozenset({
    "Tsuri", "Yori", "Gaburi", "Morozashi", "Yorikiri", "Yoritaoshi",
    "Uwatenage", "Hikiotoshi", "Tsuridashi", "Abisetaoshi",
})
GAIN_OR_ESTABLISH_GRIP = frozenset({
    "Gain Left Grip", "Gain Right Grip", "Uwate", "Shitate",
    "Attempt Two-Handed Grip", "Attempt Deep Outside Grip",
    "Attempt Deep Inside Grip", "Morozashi",
})
GRIP_UTILITY = GAIN_OR_ESTABLISH_GRIP | frozenset({
    "Tsuri", "Yori", "Gaburi", "Ottsuke", "Kannuki",
    "Yorikiri", "Yoritaoshi", "Uwatenage", "Hikiotoshi",
    "Tsuridashi", "Abisetaoshi",
})
GRIP_BUILDING_PROTECTED = GAIN_OR_ESTABLISH_GRIP
REMOVE_GRIP = frozenset({"Tsuki", "Ottsuke", "Kannuki", "Kotenage"})
VOLUNTARY_NEGATIVE = frozenset({"Pull", "Use the Tawara", "Give Ground"})
LOSES_POSITION = frozenset({"Pull", "Use the Tawara", "Give Ground"})
LOSES_MOMENTUM = frozenset({
    "Headlong Charge", "Attempt Two-Handed Grip", "Attempt Deep Outside Grip",
    "Attempt Deep Inside Grip", "Pull", "Get Underneath",
})
DOWNSIDE_GAMBLE = frozenset({
    "Headlong Charge", "Attempt Two-Handed Grip", "Attempt Deep Outside Grip",
    "Attempt Deep Inside Grip", "Get Underneath", "Henka",
})
PROVIDES_POWER = frozenset({
    "Headlong Charge", "Nodowa", "Harite", "Immovable", "Give Ground",
    "Oshitaoshi", "Yoritaoshi", "Tsuridashi",
})
GRIP_DISRUPTION = frozenset({"Tsuki", "Ottsuke", "Kannuki"})
DRAWS_OR_ADDS_PLAY = frozenset({
    "Oshi", "Tsuki", "Tsuppari", "Salt Throw", "Stare Down",
    "Henka", "Read the Move", "Regain Balance", "Give Ground",
    "Tsukidashi", "Tsukitaoshi",
})


PUSH_AMOUNT: dict[str, int] = {
    "Oshi": 1,
    "Tsuppari": 1,
    "Headlong Charge": 1,
    "Gain Right Grip": 1,
    "Shitate": 2,
    "Belt Slap": 1,
    "Tsuri": 3,
    "Gaburi": 3,
    "Get Underneath": 1,
    "Morozashi": 1,
}


POWER_PROVIDED: dict[str, int] = {
    "Headlong Charge": 1,
    "Nodowa": 2,
    "Harite": 1,
    "Immovable": 1,
    "Give Ground": 1,
    "Oshitaoshi": 1,
    "Yoritaoshi": 1,
    "Tsuridashi": 2,
}


@dataclass(frozen=True)
class ExclusionResult:
    wrestler_name: str
    difficulty: int
    target: int
    excluded_ids: frozenset[int]


def _reserved_names(wrestler_name: str) -> set[str]:
    wrestler = ORIGINAL_WRESTLERS[wrestler_name].build()
    return {
        wrestler.starting_kimarite.name,
        wrestler.prepared_tachiai_card.name,
        wrestler.top_of_deck_card.name,
    }


def eligible_cards(wrestler_name: str) -> list[Card]:
    reserved = _reserved_names(wrestler_name)
    return [
        card
        for card in CARD_POOL
        if card.card_id not in UNIVERSALLY_PROTECTED_IDS
        and card.name not in reserved
    ]


def _generic_tail(card: Card) -> tuple:
    return (card.card_id,)


def exclusion_key(wrestler_name: str, card: Card) -> tuple:
    name = card.name

    if wrestler_name == "Ura":
        if name in POWER_COMPARISON:
            return (0, *_generic_tail(card))
        if name in SPIRIT_COMPARISON:
            return (1, *_generic_tail(card))
        if name in POWER_THRESHOLD:
            return (2, *_generic_tail(card))
        return (3, *_generic_tail(card))

    if wrestler_name == "Oshoma":
        push = PUSH_AMOUNT.get(name, 0)
        if push >= 2:
            return (0, -push, *_generic_tail(card))
        if push and name in PROVIDES_POWER:
            return (1, -push, *_generic_tail(card))
        if push:
            return (2, -push, *_generic_tail(card))
        return (3, *_generic_tail(card))

    if wrestler_name == "Asakoryu":
        if name in GAIN_OR_ESTABLISH_GRIP:
            return (0, *_generic_tail(card))
        if name in POWER_COMPARISON:
            return (1, *_generic_tail(card))
        if name in POWER_THRESHOLD:
            return (2, *_generic_tail(card))
        return (3, *_generic_tail(card))

    if wrestler_name == "Wakamotoharu":
        if name in SPIRIT_COMPARISON:
            return (0, *_generic_tail(card))
        if name in REMOVE_GRIP:
            return (1, *_generic_tail(card))
        return (2, -card.spirit, *_generic_tail(card))

    if wrestler_name == "Hoshoryu":
        if name in REMOVE_GRIP:
            return (0, *_generic_tail(card))
        if name in VOLUNTARY_NEGATIVE:
            return (1, *_generic_tail(card))
        if name in DOWNSIDE_GAMBLE:
            return (2, *_generic_tail(card))
        return (3, *_generic_tail(card))

    if wrestler_name == "Abi":
        return (
            0 if card.spirit == 0 else 1,
            -PUSH_AMOUNT.get(name, 0),
            *_generic_tail(card),
        )

    if wrestler_name == "Tobizaru":
        if name in POWER_COMPARISON:
            return (0, *_generic_tail(card))
        if name in POWER_THRESHOLD:
            return (1, *_generic_tail(card))
        if name in PROVIDES_POWER:
            return (2, *_generic_tail(card))
        return (3, *_generic_tail(card))

    if wrestler_name == "Fujinokawa":
        if name in LOSES_POSITION:
            return (0, *_generic_tail(card))
        if name in LOSES_MOMENTUM:
            return (1, *_generic_tail(card))
        if name in REQUIRES_GRIP:
            return (2, *_generic_tail(card))
        return (3, *_generic_tail(card))

    if wrestler_name == "Houdan":
        if name in REQUIRES_GRIP:
            return (0, *_generic_tail(card))
        if name in GAIN_OR_ESTABLISH_GRIP:
            return (1, *_generic_tail(card))
        return (2, -card.technique, *_generic_tail(card))

    if wrestler_name == "Takanosho":
        no_access = name not in DRAWS_OR_ADDS_PLAY
        grip_card = name in (REQUIRES_GRIP | GAIN_OR_ESTABLISH_GRIP)
        return (
            0 if no_access else 1,
            0 if grip_card else 1,
            POWER_PROVIDED.get(name, 0),
            *_generic_tail(card),
        )

    if wrestler_name == "Tochinoshin":
        if name in SPIRIT_COMPARISON:
            return (0, *_generic_tail(card))
        no_grip_or_push = (
            name not in GRIP_UTILITY
            and PUSH_AMOUNT.get(name, 0) == 0
        )
        if no_grip_or_push:
            return (1, card.technique + card.power, *_generic_tail(card))
        return (2, card.technique + card.power, *_generic_tail(card))

    if wrestler_name == "Tamawashi":
        if name in VOLUNTARY_NEGATIVE:
            return (0, *_generic_tail(card))
        neither = name not in PROVIDES_POWER and name not in GRIP_DISRUPTION
        if neither:
            return (1, card.power + card.technique, *_generic_tail(card))
        return (2, card.power + card.technique, *_generic_tail(card))

    if wrestler_name == "Daieisho":
        if name in REQUIRES_GRIP:
            return (0, *_generic_tail(card))
        if name in GAIN_OR_ESTABLISH_GRIP:
            return (1, *_generic_tail(card))
        return (2, card.power + card.spirit, *_generic_tail(card))

    if wrestler_name == "Shishi":
        protected = name in GRIP_BUILDING_PROTECTED
        candidate = card.technique > 0 and not protected
        return (
            0 if candidate else 1,
            card.power + card.spirit,
            *_generic_tail(card),
        )

    if wrestler_name == "Kotozakura":
        neither = card.power == 0 and name not in GRIP_UTILITY
        return (
            0 if neither else 1,
            card.power,
            card.technique,
            *_generic_tail(card),
        )

    raise KeyError(f"No exclusion priority registered for {wrestler_name!r}.")


def exclusions_for_difficulty(
    wrestler_name: str,
    difficulty: int,
) -> ExclusionResult:
    target = max(0, min(len(eligible_cards(wrestler_name)), 7 + difficulty))
    ranked = sorted(
        eligible_cards(wrestler_name),
        key=lambda card: exclusion_key(wrestler_name, card),
    )
    return ExclusionResult(
        wrestler_name=wrestler_name,
        difficulty=difficulty,
        target=target,
        excluded_ids=frozenset(card.card_id for card in ranked[:target]),
    )
