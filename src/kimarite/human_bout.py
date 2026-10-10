"""Incremental human-vs-AI bout with interactive card access and card play.

AI and human use the same rules. Human card access pauses before modifying the
authoritative state; choosing which cards to keep replays the start phase on a
clone and commits only a complete, validated choice.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from .actions import CardView, PlayerObservation, _view, legal_actions, observe, submit_card_action
from .controllers import TurnController, controller_for_mode
from .effects import IllegalPlay
from .models import BoutState, Card, Side
from .setup import BoutConfig, create_prepared_bout
from .tachiai import TachiaiComparison
from .turns import end_exchange_turn, start_exchange_turn


@dataclass(frozen=True)
class CardSelection:
    """Cards visible to the human during a Technique or Grip card access."""
    options: tuple[CardView, ...]
    keep: int


class _NeedCardSelection(Exception):
    def __init__(self, looked: list[Card], keep: int) -> None:
        self.looked = looked
        self.keep = keep


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
    pending_selection: CardSelection | None = None
    ai_turn_played: bool = False

    @classmethod
    def new(
        cls,
        config: BoutConfig,
        *,
        human_side: Side = Side.A,
        ai_mode: str = "tactical",
        max_turns: int = 100,
        tachiai_sacrifice: int | None = None,
    ) -> "HumanBout":
        if max_turns <= 0:
            raise ValueError("max_turns must be positive")
        prepared = create_prepared_bout(
            config, sacrifice_choices={human_side: tachiai_sacrifice},
            human_choice_side=human_side,
        )
        session = cls(
            prepared.state,
            prepared.comparison,
            human_side,
            controller_for_mode(ai_mode),
            max_turns,
        )
        session.advance()
        return session

    @classmethod
    def new_styles(cls, human_style: str, opponent_style: str, *, seed: int = 0,
                   max_turns: int = 100, tachiai_sacrifice: int | None = None):
        """Begin an archetype-versus-archetype human game."""
        from .style_builds_v5 import build_style
        from .style_ai_v5 import play_style_turn
        from .tachiai import compare_tachiai, first_exchange_side
        from .tachiai_effects import resolve_prepared_tachiai
        from .turns import apply_initial_power
        if max_turns <= 0:
            raise ValueError("max_turns must be positive")
        a = build_style(human_style, seed=seed, ranking=1)
        b = build_style(opponent_style, seed=seed + 1009, ranking=2)
        state = BoutState(a.fighter, b.fighter)
        state.human_choice_side = Side.A
        comparison = compare_tachiai(a.fighter.wrestler, b.fighter.wrestler)
        apply_initial_power(state, comparison)
        resolve_prepared_tachiai(
            state, comparison, sacrifice_choices={Side.A: tachiai_sacrifice}
        )
        if state.winner is None:
            state.active_side = first_exchange_side(comparison, a.fighter.wrestler, b.fighter.wrestler)
        def controller(state, side, comparison):
            return play_style_turn(state, side, comparison, opponent_style)
        session = cls(state, comparison, Side.A, controller, max_turns)
        session.advance()
        return session

    @property
    def finished(self) -> bool:
        return self.state.winner is not None or self.stopped_reason is not None

    def view(self) -> PlayerObservation:
        return observe(self.state, self.human_side)

    @property
    def pending_kimarite_search(self) -> tuple[CardView, ...] | None:
        if not self.state.pending_kimarite_searches:
            return None
        side, _ = self.state.pending_kimarite_searches[0]
        if side is not self.human_side:
            return None
        return tuple(_view(card) for card in self.state.fighter(side).draw_pile if card.is_kimarite)

    def choose_kimarite_search(self, index: int) -> None:
        options = self.pending_kimarite_search
        if options is None or not self.awaiting_human:
            raise IllegalPlay("No Kimarite search choice is pending.")
        eligible = [i for i, c in enumerate(self.state.fighter(self.human_side).draw_pile) if c.is_kimarite]
        if type(index) is not int or index not in eligible:
            raise IllegalPlay("Choose an eligible Kimarite Draw Pile index.")
        side, source = self.state.pending_kimarite_searches.pop(0)
        fighter = self.state.fighter(side)
        selected = fighter.draw_pile.pop(index)
        fighter.kimarite_zone.append(selected)
        self.state.log(f"{fighter.wrestler.name} searches {selected.name} into the Kimarite Zone after {source}.")
        if self.state.pending_kimarite_searches:
            return
        if self.ai_turn_played:
            self.ai_turn_played = False
            self._finish_turn()
        if not self.finished:
            self.advance()

    def actions(self):
        if not self.awaiting_human or self.finished or self.pending_selection or self.pending_kimarite_search is not None:
            return ()
        return legal_actions(self.state, self.human_side)

    def advance(self) -> None:
        """Run the engine and AI until a human choice or terminal state."""
        self.awaiting_human = False
        if self.pending_kimarite_search is not None:
            self.awaiting_human = True
            return
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
                    if side is self.human_side:
                        # A card-access request must not partially consume
                        # a turn, a discard, or the exhaustion Power penalty.
                        trial = deepcopy(self.state)

                        def request_selection(looked: list[Card], keep: int) -> list[Card]:
                            raise _NeedCardSelection(looked, keep)

                        try:
                            start_exchange_turn(
                                trial, side, self.comparison,
                                choose_cards=request_selection,
                            )
                        except _NeedCardSelection as needed:
                            self.pending_selection = CardSelection(
                                tuple(_view(card) for card in needed.looked),
                                needed.keep,
                            )
                            self.awaiting_human = True
                            return
                        self.state.__dict__.update(trial.__dict__)
                    else:
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
            if self.pending_kimarite_search is not None:
                self.ai_turn_played = True
                self.awaiting_human = True
                return
            if self.state.winner is not None:
                break
            self._finish_turn()

    def choose_cards(self, indices: list[int] | tuple[int, ...]) -> None:
        """Keep selected looked-at cards, bottoming the rest in reveal order."""
        pending = self.pending_selection
        if self.finished or not self.awaiting_human or pending is None:
            raise IllegalPlay("No card-access selection is pending.")
        if (
            len(indices) != pending.keep
            or len(set(indices)) != len(indices)
            or any(not isinstance(i, int) or not 0 <= i < len(pending.options) for i in indices)
        ):
            raise IllegalPlay(f"Select exactly {pending.keep} distinct valid indices.")

        trial = deepcopy(self.state)

        def chosen(looked: list[Card], keep: int) -> list[Card]:
            if keep != pending.keep or tuple(_view(c) for c in looked) != pending.options:
                raise IllegalPlay("Card-access options changed unexpectedly.")
            return [looked[i] for i in indices]

        start_exchange_turn(trial, self.human_side, self.comparison, choose_cards=chosen)
        self.state.__dict__.update(trial.__dict__)
        self.pending_selection = None
        self.turn_started = True
        if self.state.winner is not None:
            self.awaiting_human = False

    def play(self, hand_index: int, *, choices: dict | None = None) -> None:
        if not self.awaiting_human or self.finished or self.pending_selection or self.pending_kimarite_search is not None:
            raise IllegalPlay("No human card-play phase is active.")
        submit_card_action(
            self.state, self.human_side, hand_index,
            choices=choices, comparison=self.comparison,
        )
        if self.state.winner is not None:
            self.awaiting_human = False

    def _finish_turn(self) -> None:
        side = self.state.active_side
        assert side is not None
        try:
            end_exchange_turn(self.state, side)
        except NotImplementedError as exc:
            self.stopped_reason = str(exc)
        self.turn_started = False

    def end_turn(self) -> None:
        if not self.awaiting_human or self.finished or self.pending_selection or self.pending_kimarite_search is not None:
            raise IllegalPlay("Finish card selection before ending the human turn.")
        self.awaiting_human = False
        self._finish_turn()
        if not self.finished:
            self.advance()
