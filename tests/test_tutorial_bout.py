import unittest

from kimarite.b10_human_session import dispatch
from kimarite.effects import ChoiceRequired, IllegalPlay
from kimarite.tutorial_bout import TutorialOpening


class TutorialBoutTest(unittest.TestCase):
    def test_guided_yorikiri_bout(self):
        opening = TutorialOpening.new()
        self.assertIsNone(opening.snapshot()["opening"])
        with self.assertRaises(ValueError):
            opening.confirm([0, 1])
        opening.confirm([0, 1, 2])
        bout = opening.start_bout()

        def keep(*indices):
            return dispatch(bout, {"type": "choose_cards", "indices": list(indices)})

        def play(name, **choices):
            index = next(i for i, card in enumerate(bout.state.fighter_a.hand) if card.name == name)
            return dispatch(bout, {"type": "play_card", "hand_index": index, "choices": choices})

        def end():
            return dispatch(bout, {"type": "end_turn"})

        comparison = bout.comparison
        self.assertEqual((comparison.wrestler_a.power, comparison.wrestler_a.technique,
                          comparison.wrestler_a.spirit), (4, 5, 8))
        self.assertEqual((comparison.power_advantage_a, comparison.technique_advantage_a,
                          comparison.spirit_advantage_a), (-1, 3, 4))
        self.assertEqual(bout.state.position, 1)
        self.assertEqual(bout.pending_selection.keep, 3)
        first = keep(0, 1, 2)
        self.assertEqual([card["name"] for card in first["human"]["hand"]], ["Oshi", "Sheer Grit", "Stare Down"])
        with self.assertRaises(IllegalPlay):
            play("Sheer Grit")
        with self.assertRaises(ChoiceRequired):
            play("Oshi")
        with self.assertRaises(IllegalPlay):
            play("Oshi", hand_index=1)
        pushed = play("Oshi", hand_index=0)
        self.assertEqual(pushed["position"], 2)
        self.assertEqual([card["name"] for card in pushed["human"]["hand"]], ["Stare Down", "Gain Right Grip"])
        right_grip = play("Gain Right Grip")
        self.assertEqual(right_grip["human"]["grip"], [0, 1])
        draw = end()
        self.assertEqual(draw["momentum"], -1)
        self.assertEqual(draw["position"], 2)
        self.assertEqual([card["name"] for card in draw["selection"]["options"]],
                         ["Regain Balance", "Attempt Deep Outside Grip", "Shove"])
        with self.assertRaises(IllegalPlay):
            keep(0, 2)
        keep(0, 1)
        self.assertEqual(play("Regain Balance")["momentum"], 0)
        self.assertEqual(play("Attempt Deep Outside Grip")["human"]["grip"], [1, 1])
        exhausted = end()
        self.assertGreaterEqual(exhausted["human"]["discard_count"], 7)
        deep_grip = keep(0, 1)
        self.assertEqual(deep_grip["human"]["grip"], [2, 1])
        self.assertFalse(any("loses 1 Power to Exhaustion" in event for event in deep_grip["events"]))
        ready = play("Oshidashi")
        self.assertEqual([card["name"] for card in ready["human"]["kimarite"]],
                         ["Yorikiri", "Oshidashi"])
        result = end()
        self.assertEqual((result["winner"], result["win_method"]), ("A", "Yorikiri"))
