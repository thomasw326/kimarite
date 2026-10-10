"""Approved 15-archetype preferences from the live Sumo Styles sheet.

The weights and Top 7 are read from columns U:Z and AB:AH, respectively,
on 2026-10-09. Preserve sheet spellings; map aliases only at catalog lookup.
This module intentionally does not alter the V4.5 fixed 30-wrestler tester.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Sequence

from .catalog import CARD_POOL, STARTING_KIMARITE
from .models import Card

_SOURCE_JSON = r'''[
  {
    "name": "Heavy Hitter",
    "power": 4,
    "technique": 0,
    "spirit": 2,
    "primary": "Power",
    "secondary": "Spirit",
    "priority": "Power",
    "kimarite": [
      "Oshidashi",
      "Oshitaoshi"
    ],
    "preferred": [
      "Oshidashi",
      "Harite",
      "Shove",
      "Tsuppari",
      "Immovable",
      "Nodowa",
      "Belt Slap"
    ],
    "weights": [
      2,
      -1,
      -2,
      -2,
      0,
      2
    ]
  },
  {
    "name": "Bulldozer",
    "power": 3,
    "technique": 0,
    "spirit": 3,
    "primary": "Power",
    "secondary": "Spirit",
    "priority": "Spirit",
    "kimarite": [
      "Oshidashi",
      "Oshitaoshi"
    ],
    "preferred": [
      "Oshidashi",
      "Belt Slap",
      "Explosive Step",
      "Headlong Charge",
      "Oshi",
      "Stare Down",
      "Shove"
    ],
    "weights": [
      1,
      2,
      -2,
      -2,
      2,
      2
    ]
  },
  {
    "name": "Charger",
    "power": 2,
    "technique": 0,
    "spirit": 4,
    "primary": "Spirit",
    "secondary": "Power",
    "priority": "Spirit",
    "kimarite": [
      "Oshidashi",
      "Yoritaoshi"
    ],
    "preferred": [
      "Explosive Step",
      "Headlong Charge",
      "Oshidashi",
      "Belt Slap",
      "Stare Down",
      "Oshi",
      "Shove"
    ],
    "weights": [
      1,
      3,
      -2,
      -1,
      2,
      2
    ]
  },
  {
    "name": "Pressure Fighter",
    "power": 3,
    "technique": 0,
    "spirit": 3,
    "primary": "Spirit",
    "secondary": "Power",
    "priority": "Power",
    "kimarite": [
      "Tsukidashi",
      "Tsukitaoshi"
    ],
    "preferred": [
      "Oshidashi",
      "Oshi",
      "Tsuppari",
      "Belt Slap",
      "Shove",
      "Tsukidashi",
      "Tsuki"
    ],
    "weights": [
      2,
      1,
      -2,
      -3,
      1,
      2
    ]
  },
  {
    "name": "Power Grappler",
    "power": 4,
    "technique": 2,
    "spirit": 0,
    "primary": "Power",
    "secondary": "Technique",
    "priority": "Power",
    "kimarite": [
      "Tsuridashi",
      "Abisetaoshi"
    ],
    "preferred": [
      "Abisetaoshi",
      "Tsuridashi",
      "Tsuri",
      "Yoritaoshi",
      "Gain Left Grip",
      "Gain Right Grip",
      "Hold Position"
    ],
    "weights": [
      2,
      -2,
      0,
      2,
      0,
      0
    ]
  },
  {
    "name": "Unorthodox Powerhouse",
    "power": 3,
    "technique": 3,
    "spirit": 0,
    "primary": "Power",
    "secondary": "Technique",
    "priority": "Technique",
    "kimarite": [
      "Hatakikomi",
      "Kotenage"
    ],
    "preferred": [
      "Henka",
      "Regain Balance",
      "Nodowa",
      "Get Underneath",
      "Kannuki",
      "Kotenage",
      "Ottsuke"
    ],
    "weights": [
      2,
      -2,
      2,
      -1,
      0,
      0
    ]
  },
  {
    "name": "The Technician",
    "power": 2,
    "technique": 4,
    "spirit": 0,
    "primary": "Technique",
    "secondary": "Power",
    "priority": "Technique",
    "kimarite": [
      "Uwatenage",
      "Shitatenage"
    ],
    "preferred": [
      "Power Water",
      "Sidestep",
      "Use the Tawara",
      "Pull",
      "Uwatenage",
      "Katasukashi",
      "Gain Right Grip"
    ],
    "weights": [
      1,
      -2,
      3,
      1,
      0,
      -1
    ]
  },
  {
    "name": "The Arsenal",
    "power": 3,
    "technique": 3,
    "spirit": 0,
    "primary": "Technique",
    "secondary": "Power",
    "priority": "Power",
    "kimarite": [
      "Uwatenage",
      "Shitatenage"
    ],
    "preferred": [
      "Power Water",
      "Sidestep",
      "Use the Tawara",
      "Uwatenage",
      "Gain Right Grip",
      "Pull",
      "Shiko Stomp"
    ],
    "weights": [
      1,
      -1,
      2,
      1,
      0,
      -1
    ]
  },
  {
    "name": "Mawashi Specialist",
    "power": 0,
    "technique": 4,
    "spirit": 2,
    "primary": "Technique",
    "secondary": "Spirit",
    "priority": "Technique",
    "kimarite": [
      "Shitatenage",
      "Shitatenage"
    ],
    "preferred": [
      "Attempt Deep Inside Grip",
      "Attempt Two-Handed Grip",
      "Shitatenage",
      "Morozashi",
      "Shitate",
      "Gain Right Grip",
      "Hikiotoshi"
    ],
    "weights": [
      -1,
      0,
      2,
      2,
      0,
      -1
    ]
  },
  {
    "name": "Opportunist",
    "power": 0,
    "technique": 3,
    "spirit": 3,
    "primary": "Technique",
    "secondary": "Spirit",
    "priority": "Spirit",
    "kimarite": [
      "Hatakikomi",
      "Hikiotoshi"
    ],
    "preferred": [
      "Katasukashi",
      "Salt Throw",
      "Hikiotoshi",
      "Pull",
      "Attempt Deep Inside Grip",
      "Tottari",
      "Ottsuke"
    ],
    "weights": [
      -2,
      1,
      2,
      -1,
      -2,
      0
    ]
  },
  {
    "name": "Fast Grappler",
    "power": 0,
    "technique": 2,
    "spirit": 4,
    "primary": "Spirit",
    "secondary": "Technique",
    "priority": "Spirit",
    "kimarite": [
      "Yorikiri",
      "Yorikiri"
    ],
    "preferred": [
      "Headlong Charge",
      "Explosive Step",
      "Yorikiri",
      "Gaburi",
      "Yori",
      "Shitatenage",
      "Belt Slap"
    ],
    "weights": [
      -2,
      2,
      0,
      2,
      2,
      1
    ]
  },
  {
    "name": "Disruptor",
    "power": 0,
    "technique": 3,
    "spirit": 3,
    "primary": "Spirit",
    "secondary": "Technique",
    "priority": "Technique",
    "kimarite": [
      "Kotenage",
      "Tottari"
    ],
    "preferred": [
      "Reset to Neutral",
      "Tsukiotoshi",
      "Read the Move",
      "Salt Throw",
      "Get Underneath",
      "Tsuki",
      "Ottsuke"
    ],
    "weights": [
      -2,
      0,
      2,
      -2,
      2,
      -1
    ]
  },
  {
    "name": "Mountain",
    "power": 4,
    "technique": 1,
    "spirit": 1,
    "primary": "Power",
    "secondary": "Power",
    "priority": "Power",
    "kimarite": [
      "Oshitaoshi",
      "Abisetaoshi"
    ],
    "preferred": [
      "Immovable",
      "Hold Position",
      "Harite",
      "Nodowa",
      "Kannuki",
      "Katasukashi",
      "Oshidashi"
    ],
    "weights": [
      3,
      -2,
      -1,
      -2,
      -2,
      1
    ]
  },
  {
    "name": "The Specialist",
    "power": 1,
    "technique": 4,
    "spirit": 1,
    "primary": "Technique",
    "secondary": "Technique",
    "priority": "Technique",
    "kimarite": [
      "Katasukashi",
      "Tsukiotoshi"
    ],
    "preferred": [
      "Katasukashi",
      "Sidestep",
      "Pull",
      "Tsukiotoshi",
      "Use the Tawara",
      "Kotenage",
      "Reset to Neutral"
    ],
    "weights": [
      -1,
      -1,
      2,
      -1,
      0,
      -1
    ]
  },
  {
    "name": "Speed Demon",
    "power": 1,
    "technique": 1,
    "spirit": 4,
    "primary": "Spirit",
    "secondary": "Spirit",
    "priority": "Spirit",
    "kimarite": [
      "Oshidashi",
      "Oshidashi"
    ],
    "preferred": [
      "Headlong Charge",
      "Explosive Step",
      "Belt Slap",
      "Shove",
      "Stare Down",
      "Oshidashi",
      "Oshi"
    ],
    "weights": [
      -2,
      2,
      -2,
      -2,
      2,
      2
    ]
  }
]'''

# The spreadsheet shortens one in-game card title.
ALIASES = {"Explosive Step": "Explosive Step — Fumikomi"}


@dataclass(frozen=True)
class StyleProfile:
    name: str
    stats: tuple[int, int, int]
    primary: str
    secondary: str
    preferred_tachiai: str
    starting_kimarite: tuple[str, str]
    preferred_cards: tuple[str, ...]
    six_axis_weights: tuple[int, ...]


def _load() -> dict[str, StyleProfile]:
    result = {}
    for record in json.loads(_SOURCE_JSON):
        profile = StyleProfile(
            name=record["name"],
            stats=(record["power"], record["technique"], record["spirit"]),
            primary=record["primary"],
            secondary=record["secondary"],
            preferred_tachiai=record["priority"],
            starting_kimarite=tuple(record["kimarite"]),
            preferred_cards=tuple(record["preferred"]),
            six_axis_weights=tuple(record["weights"]),
        )
        result[profile.name] = profile
    return result


STYLES: dict[str, StyleProfile] = _load()


def resolve_card(name: str) -> Card:
    canonical = ALIASES.get(name, name)
    found = [card for card in (*CARD_POOL, *STARTING_KIMARITE) if card.name == canonical]
    if not found:
        raise KeyError(f"Style card {name!r} is missing from the card catalog.")
    return found[0]


def preferred_card_pool(profile: StyleProfile) -> tuple[Card, ...]:
    """Return the archetype's seven ranked favorites, with no inferred copies."""
    return tuple(resolve_card(name) for name in profile.preferred_cards)


def preferred_kimarite(profile: StyleProfile) -> tuple[Card, Card]:
    return tuple(resolve_card(name) for name in profile.starting_kimarite)


def preference_bonus(profile: StyleProfile, card_name: str) -> int:
    """Rank-based soft affinity, never a rule requiring any preferred card."""
    canonical = ALIASES.get(card_name, card_name)
    for index, name in enumerate(profile.preferred_cards):
        if ALIASES.get(name, name) == canonical:
            return 7 - index
    return 0


def ranked_pool(profile: StyleProfile, cards: Sequence[Card]) -> list[Card]:
    """Rank each supplied eligible card, retaining all nonfavorites.

    Stable sorting preserves the existing deck order among equal preferences.
    """
    return sorted(cards, key=lambda card: -preference_bonus(profile, card.name))
