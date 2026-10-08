from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, IntEnum


class GripState(IntEnum):
    NONE = 0
    GRIP = 1
    DEEP = 2


class Side(str, Enum):
    A = "A"
    B = "B"


class Stat(str, Enum):
    POWER = "Power"
    TECHNIQUE = "Technique"
    SPIRIT = "Spirit"


@dataclass(frozen=True)
class Card:
    card_id: int
    name: str
    power: int = 0
    technique: int = 0
    spirit: int = 0
    is_kimarite: bool = False

    def orbs(self, stat: Stat) -> int:
        if stat is Stat.POWER:
            return self.power
        if stat is Stat.TECHNIQUE:
            return self.technique
        return self.spirit


@dataclass(frozen=True)
class Wrestler:
    name: str
    base_power: int
    base_technique: int
    base_spirit: int
    starting_kimarite: Card
    prepared_tachiai_card: Card
    top_of_deck_card: Card
    primary: Stat = Stat.POWER
    secondary: Stat = Stat.TECHNIQUE
    tertiary: Stat = Stat.SPIRIT
    ranking: int | None = None


@dataclass
class TemporaryInstance:
    card: Card
    entered_turn: int
    entered_phase: str
    opponent_gained_push_while_active: bool = False


@dataclass
class FighterState:
    wrestler: Wrestler
    draw_pile: list[Card] = field(default_factory=list)
    hand: list[Card] = field(default_factory=list)
    discard_pile: list[Card] = field(default_factory=list)
    kimarite_zone: list[Card] = field(default_factory=list)
    temporary_zone: list[TemporaryInstance] = field(default_factory=list)
    power: int = 0
    left_grip: GripState = GripState.NONE
    right_grip: GripState = GripState.NONE
    plays_remaining: int = 2
    cards_played_this_turn: int = 0
    played_this_turn: list[Card] = field(default_factory=list)
    first_exchange_turn: bool = True
    technique_reward_pending: bool = True
    technique_look_adjustment: int = 0
    spirit_reward_pending: bool = True
    bonus_turns_queued: int = 0
    lost_position_this_turn: bool = False
    opponent_grip_reduced_this_turn: bool = False
    tottari_counter_event_turn: int = -100
    gained_push_this_turn: bool = False
    gained_momentum_this_turn: bool = False

    @property
    def total_grip(self) -> int:
        return int(self.left_grip) + int(self.right_grip)


@dataclass
class BoutState:
    fighter_a: FighterState
    fighter_b: FighterState
    momentum: int = 0
    position: int = 0
    side_by_side_owner: Side | None = None
    side_by_side_distance: int = 0
    active_side: Side | None = None
    turn_number: int = 0
    winner: Side | None = None
    win_method: str | None = None
    win_source: str | None = None
    card_plays: list[tuple[Side, str]] = field(default_factory=list)
    kimarite_removals: list[tuple[Side, str]] = field(default_factory=list)
    temporary_outcomes: list[tuple[Side, str, str]] = field(default_factory=list)
    event_log: list[str] = field(default_factory=list)

    def fighter(self, side: Side) -> FighterState:
        return self.fighter_a if side is Side.A else self.fighter_b

    def opponent(self, side: Side) -> FighterState:
        return self.fighter_b if side is Side.A else self.fighter_a

    @staticmethod
    def opponent_side(side: Side) -> Side:
        return Side.B if side is Side.A else Side.A

    @staticmethod
    def sign(side: Side) -> int:
        return 1 if side is Side.A else -1

    def log(self, message: str) -> None:
        self.event_log.append(message)

    def declare_winner(self, side: Side, method: str) -> None:
        if self.winner is None:
            self.winner = side
            self.win_method = method
            self.log(f"{self.fighter(side).wrestler.name} wins by {method}.")
