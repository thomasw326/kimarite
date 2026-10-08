from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


class GripState(IntEnum):
    NONE = 0
    GRIP = 1
    DEEP = 2


@dataclass(frozen=True)
class Card:
    card_id: int
    name: str
    power: int = 0
    technique: int = 0
    spirit: int = 0
    is_kimarite: bool = False


@dataclass(frozen=True)
class Wrestler:
    name: str
    base_power: int
    base_technique: int
    base_spirit: int
    starting_kimarite: Card
    prepared_tachiai_card: Card
    top_of_deck_card: Card


@dataclass
class BoutState:
    wrestler_a: Wrestler
    wrestler_b: Wrestler
    momentum: int = 0
    position: int = 0
    power_a: int = 0
    power_b: int = 0
    left_grip_a: GripState = GripState.NONE
    right_grip_a: GripState = GripState.NONE
    left_grip_b: GripState = GripState.NONE
    right_grip_b: GripState = GripState.NONE
    winner: str | None = None
    win_method: str | None = None
    event_log: list[str] = field(default_factory=list)

    def log(self, message: str) -> None:
        self.event_log.append(message)
