"""A fixed teaching bout played through the normal Exchange rules."""
from .b11_pending_session import PendingB11Session
from .b11_player_opening import PlayerOpening
from .b11_player_tachiai import compare_player_tachiai
from .b11_tachiai_phase import PendingPlayerTachiai
from .catalog import card_by_name
from .effects import IllegalPlay
from .human_bout import HumanBout
from .models import BoutState, FighterState, Side, Wrestler
from .playing import play_card
from .tachiai import first_exchange_side
from .tachiai_effects import resolve_prepared_tachiai
from .turns import apply_initial_power

OPENING = ("Sheer Grit", "Shikiri", "Yorikiri")
PLAYER_STATS = {"power": 2, "technique": 1, "spirit": 1}
PLAYER_DRAWS = (
    "Oshi", "Sheer Grit", "Gain Right Grip", "Tsuki",
    "Regain Balance", "Attempt Deep Outside Grip", "Shove",
    "Power Water", "Tsuppari", "Ottsuke",
    "Oshidashi", "Pull", "Sonkyo", "Nokotta!", "Belt Slap", "Salt Throw",
)
OPPONENT_DRAWS = (
    "Shove", "Stare Down", "Tsuki", "Shiko Stomp", "Sonkyo",
    "Harite", "Gain Left Grip", "Tsuppari", "Belt Slap",
)
OPPONENT_PLAYS = {
    1: ("Shove",),
    3: ("Shiko Stomp", "Sonkyo"),
    5: ("Harite", "Gain Left Grip"),
}
PLAYER_STEPS = (
    ("choose_cards", ("Oshi", "Sheer Grit")),
    ("play_card", "Oshi"),
    ("play_card", "Gain Right Grip"),
    ("end_turn", None),
    ("choose_cards", ("Regain Balance", "Attempt Deep Outside Grip")),
    ("play_card", "Regain Balance"),
    ("play_card", "Attempt Deep Outside Grip"),
    ("end_turn", None),
    ("choose_cards", ("Oshidashi",)),
    ("play_card", "Oshidashi"),
    ("end_turn", None),
)


class TutorialOpening(PendingB11Session):
    @classmethod
    def new(cls):
        cards = [card_by_name(name) for name in OPENING]
        phase = PendingPlayerTachiai(PlayerOpening.from_names(cards, list(OPENING)))
        return cls("Your Rikishi", "Training Partner", phase, created_stats=PLAYER_STATS)

    def snapshot(self):
        return {**super().snapshot(), "tutorial_stats": PLAYER_STATS.copy()}

    def confirm(self, indices):
        if not isinstance(indices, list) or len(indices) != 3:
            raise ValueError("Commit all three cards for this practice bout.")
        return super().confirm(indices)

    def start_bout(self):
        decision = self.phase.decision
        yorikiri = card_by_name("Yorikiri")
        oshi = card_by_name("Oshi")
        player = Wrestler(self.human, PLAYER_STATS["power"], PLAYER_STATS["technique"],
                          PLAYER_STATS["spirit"], yorikiri, oshi, oshi)
        opponent = Wrestler(self.opponent, 0, 5, 0, card_by_name("Oshidashi"),
                            card_by_name("Regain Balance"), card_by_name("Shove"))
        own = FighterState(player, draw_pile=[card_by_name(name) for name in PLAYER_DRAWS])
        foe = FighterState(opponent, draw_pile=[card_by_name(name) for name in OPPONENT_DRAWS])
        state = BoutState(own, foe)
        state.b11_explain_wins = True
        comparison = compare_player_tachiai(player, opponent, decision.committed)
        apply_initial_power(state, comparison)
        resolve_prepared_tachiai(state, comparison, committed_cards={Side.A: decision.committed})
        state.active_side = first_exchange_side(comparison, player, opponent)
        session = TutorialBout(state, comparison, Side.A, _opponent_turn, annotate_turns=True)
        session.b11_opening = {
            "allocated": decision.allocated, "committed": decision.committed,
            "retained": decision.retained,
        }
        session.advance()
        return session


def _opponent_turn(state, side, _comparison):
    fighter = state.fighter(side)
    for name in OPPONENT_PLAYS[state.turn_number]:
        play_card(state, side, next(card for card in fighter.hand if card.name == name))


class TutorialBout(HumanBout):
    tutorial_step = 0

    def check_instruction(self, command):
        if self.finished:
            raise IllegalPlay("The practice bout is already over.")
        action, target = PLAYER_STEPS[self.tutorial_step]
        if command.get("type") == action:
            if action == "end_turn":
                return
            if action == "choose_cards" and self.pending_selection:
                options = self.pending_selection.options
                indices = command.get("indices", [])
                if (isinstance(indices, list) and len(indices) == self.pending_selection.keep
                        and all(type(index) is int and 0 <= index < len(options) for index in indices)):
                    names = [options[index].name for index in indices]
                    if set(target).issubset(names):
                        return
            if action == "play_card":
                hand = self.state.fighter(self.human_side).hand
                index = command.get("hand_index")
                if type(index) is int and 0 <= index < len(hand) and hand[index].name == target:
                    return
        raise IllegalPlay("Follow your oyakata’s current instruction to continue the practice bout.")
