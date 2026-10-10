"""Incremental human-vs-AI bout driver using the existing rules engine.

A session stops at human card choices. Card-access selection still follows the
engine's automatic Primary/Secondary ranking; manual look/keep is a later step.
"""
from __future__ import annotations

from dataclasses import dataclass

from .actions import PlayerObservation, legal_actions, observe, submit_card_action
from .controllers import TurnController, controller_for_mode
from .effects import IllegalPlay
from .models import BoutState, Side
from .setup import BoutConfig, create_prepared_bout
from .tachiai import TachiaiComparison
from .turns import end_exchange_turn, start_exchange_turn


@dataclass
class HumanBout:
    state: BoutState
    comparison: TachiaiComparison
    human_side: Side
    ai_controller: TurnController
    max_turns: int = 100
    awaiting_human: bool = False
    turn_started: bool = False
    stopped_reason: str | None = None

    @classmethod
    def new(
        cls,
        config: BoutConfig,
        *,
        human_side: Side = Side.A,
        ai_mode: str = "tactical",
        max_turns: int = 100,
    ) -> "HumanBout":
        if max_turns <= 0:
            raise ValueError("max_turns must be positive")
        prepared = create_prepared_bout(config)
        session = cls(
            prepared.state,
            prepared.comparison,
            human_side,
            controller_for_mode(ai_mode),
            max_turns,
        )
        session.advance()
        return session

    @property
    def finished(self) -> bool:
        return self.state.winner is not None or self.stopped_reason is not None

    def view(self) -> PlayerObservation:
        return observe(self.state, self.human_side)

    def actions(self):
        if not self.awaiting_human or self.finished:
            return ()
        return legal_actions(self.state, self.human_side)

    def advance(self) -> None:
        """Run the engine and AI until a human choice or terminal state."""
        self.awaiting_human = False
        while not self.finished:
            side = self.state.active_side
            if side is None:
                self.stopped_reason = "No active wrestler was determined."
                break

            if not self.turn_started:
                if self.state.turn_number >= self.max_turns:
                    self.stopped_reason = f"Turn limit {self.max_turns} reached."
                    break
                try:
                    start_exchange_turn(self.state, side, self.comparison)
                except NotImplementedError as exc:
                    self.stopped_reason = str(exc)
                    break
                self.turn_started = True
                if self.state.winner is not None:
                    break

            if side is self.human_side:
                self.awaiting_human = True
                return

            self.ai_controller(self.state, side, self.comparison)
            if self.state.winner is not None:
                break
            self._finish_turn()

    def _finish_turn(self) -> None:
        side = self.state.active_side
        assert side is not None
        try:
            end_exchange_turn(self.state, side)
        except NotImplementedError as exc:
            self.stopped_reason = str(exc)
        self.turn_started = False

    def play(self, hand_index: int, *, choices: dict | None = None) -> None:
        if not self.awaiting_human or self.finished:
            raise IllegalPlay("No human turn is waiting for a card action.")
        submit_card_action(
            self.state, self.human_side, hand_index, choices=choices, comparison=self.comparison
        )
        if self.state.winner is not None:
            self.awaiting_human = False

    def end_turn(self) -> None:
        if not self.awaiting_human or self.finished:
            raise IllegalPlay("There is no active human turn to end.")
        self.awaiting_human = False
        self._finish_turn()
        if not self.finished:
            self.advance()
