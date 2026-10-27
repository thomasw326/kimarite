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
    technique_keep_adjustment: int = 0
    spirit_reward_pending: bool = True
    bonus_turns_queued: int = 0
    lost_position_this_turn: bool = False
    opponent_grip_reduced_this_turn: bool = False
    gained_push_this_turn: bool = False
    gained_momentum_this_turn: bool = False
    successful_reversal_this_turn: bool = False
    unstable: bool = False
    turns_started: int = 0
    unstable_recovery_turn: int = 0

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
    disable_kimarite_exchange_effects: bool = False
    r20_active: bool = False  # Experimental gauntlet only; never enabled for normal V5 bouts.
    winner: Side | None = None
    win_method: str | None = None
    win_source: str | None = None
    tachiai_spirit_advantage_a: int = 0
    winning_kimarite_card_id: int | None = None
    card_play_ids: list[tuple[Side, int]] = field(default_factory=list)
    card_plays: list[tuple[Side, str]] = field(default_factory=list)
    first_exchange_hands: dict[Side, tuple[str, ...]] = field(default_factory=dict)
    kimarite_removals: list[tuple[Side, str]] = field(default_factory=list)
    temporary_outcomes: list[tuple[Side, str, str]] = field(default_factory=list)
    reversal_completions: list[tuple[Side, str, int]] = field(default_factory=list)
    headlong_decisions: list[tuple[Side, str, str, str | None]] = field(default_factory=list)
    position_loss_events: list[tuple[Side, int, str, int]] = field(default_factory=list)
    katasukashi_win_sources: list[str] = field(default_factory=list)
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
            # B11-only presentation: give Power-loss knockdowns traditional
            # Kimarite names. This does not alter the winning condition.
            if getattr(self, "b11_explain_wins", False):
                if method == "Power":
                    wrestler = self.fighter(side).wrestler
                    highest = max(
                        (("power", wrestler.base_power),
                         ("technique", wrestler.base_technique),
                         ("spirit", wrestler.base_spirit)),
                        key=lambda pair: pair[1],
                    )[0]
                    method = {"power": "Tsukiotoshi",
                              "technique": "Hikiotoshi",
                              "spirit": "Hatakikomi"}[highest]
                    self.win_source = "power_loss"
                elif self.win_source == "ringout":
                    # A Shove-induced force-out is always Oshidashi.
                    played = self.fighter(side).played_this_turn
                    if played and played[-1].name == "Shove":
                        method = "Oshidashi"
            self.winner = side
            self.win_method = method
            if getattr(self, "b11_explain_wins", False) and not hasattr(self, "b11_victory_details"):
                source = self.win_source
                if source == "ringout":
                    explanation = (
                        "Ring-out: the winning wrestler pushed the opponent "
                        "past the ring boundary. This is an immediate win, "
                        "not a Kimarite Zone requirement check."
                    )
                elif method == "Exhaustion":
                    explanation = "Exhaustion: the opponent had no cards left to draw at the start of their turn."
                elif source == "power_loss":
                    explanation = "Power loss: the opponent's Power fell below zero during the start-of-turn Exhaustion check."
                else:
                    explanation = "The bout ended by a direct game effect, rather than a Kimarite Zone requirement check."
                self.b11_victory_details = {
                    "kimarite": method,
                    "source": source or method.lower(),
                    "requirement_text": explanation,
                    "checks": [],
                    "turn": self.turn_number,
                }
            self.log(f"{self.fighter(side).wrestler.name} wins by {method}.")
