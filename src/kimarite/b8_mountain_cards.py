"""Trial-only B8 Mountain cards; leaves the four locked decks untouched.

Ankogata: PPP. On play +1 Power, become Stable, then with Power >=6
reduce both opposing Grip levels by 1; at >=9 remove all opposing Grips
instead. One Shiko Stomp protects against the entire hostile effect.
Morozashi's existing grip-reduction immunity remains effective.

Tsuriotoshi: PP T kimarite, threshold = usable Grip level (0..4)
+ absolute Power + relative Momentum >=15. Exchange choose one +1
Power, +1 Momentum, or +1 Flexible Grip.

B8 Stability vs Unstable has not been implemented in the tested engine:
Ankogata records Stable status and a log message; no invented new bonus.
"""
from __future__ import annotations

from .models import Card, Side
from .prevention import prevent_negative_effect
from .rules import (
    effective_total_grip, gain_flexible_grip, gain_momentum,
    gain_power, reduce_grip,
)

ANKOGATA = "Ankogata"
TSURIOTOSHI = "Tsuriotoshi"
_installed = False


def _ankogata(state, side, card, context):
    gain_power(state, side, 1)
    fighter = state.fighter(side)
    fighter.is_stable = True
    state.log(f"{fighter.wrestler.name} is now Stable (B8 experimental status).")
    power = fighter.power
    if power < 6:
        return
    enemy = state.opponent_side(side)
    opponent = state.fighter(enemy)
    if not opponent.total_grip:
        return
    full_removal = power >= 9
    if prevent_negative_effect(
        state, enemy, source=ANKOGATA,
        description="remove all Grips" if full_removal else "reduce both Grips by 1 level",
    ):
        return
    amount = 2 if full_removal else 1
    for hand in ("left", "right"):
        reduce_grip(state, enemy, amount=amount, hand=hand)
    state.log(f"Ankogata {'removes all opposing Grips' if full_removal else 'reduces each opposing Grip by 1'} when permitted.")


def _tsuriotoshi_predicate(state, side):
    return (effective_total_grip(state, side)
            + state.fighter(side).power
            + state.momentum * state.sign(side)) >= 15


def _tsuriotoshi_exchange(state, side, card, context):
    if state.disable_kimarite_exchange_effects:
        return
    from .effects import ChoiceRequired
    mode = context.choice("mode")
    if mode == "power":
        gain_power(state, side, 1)
    elif mode == "momentum":
        gain_momentum(state, side, 1)
    elif mode == "grip":
        gain_flexible_grip(state, side)
    else:
        raise ChoiceRequired(card.name, "mode", ["power", "momentum", "grip"])


def install_b8_mountain_cards():
    global _installed
    if _installed:
        return
    from . import ai, effects, kimarite, kimarite_effects, playing, style_ai_v5, style_builds_v5

    assert ANKOGATA not in effects.EXCHANGE_EFFECTS
    assert TSURIOTOSHI not in kimarite.KIMARITE_PREDICATES
    existing = {c.name for c in style_builds_v5.CARD_POOL}
    assert ANKOGATA not in existing and TSURIOTOSHI not in existing

    style_builds_v5.CARD_POOL = tuple(style_builds_v5.CARD_POOL) + (
        Card(8_710_101, ANKOGATA, 3, 0, 0),
        Card(8_710_102, TSURIOTOSHI, 2, 1, 0, True),
    )
    effects.EXCHANGE_EFFECTS[ANKOGATA] = _ankogata
    kimarite.KIMARITE_PREDICATES[TSURIOTOSHI] = _tsuriotoshi_predicate

    old_play = playing.resolve_kimarite_play_effect
    def play_kimarite(state, side, card, context):
        if card.name == TSURIOTOSHI:
            return _tsuriotoshi_exchange(state, side, card, context)
        return old_play(state, side, card, context)
    playing.resolve_kimarite_play_effect = play_kimarite

    old_contexts = ai._contexts_for_card
    def contexts(state, side, card, comparison):
        if card.name == TSURIOTOSHI:
            from .effects import EffectContext
            return [
                EffectContext(comparison=comparison, choices={"mode": mode})
                for mode in ("power", "momentum", "grip")
            ]
        return old_contexts(state, side, card, comparison)
    ai._contexts_for_card = contexts

    old_progress = ai.kimarite_progress
    def progress(state, side, card):
        if card.name == TSURIOTOSHI:
            total = (effective_total_grip(state, side)
                     + state.fighter(side).power
                     + state.momentum * state.sign(side))
            return max(0.0, min(1.0, total / 15.0))
        return old_progress(state, side, card)
    ai.kimarite_progress = progress

    old_affinity = style_ai_v5.card_affinity
    def mountain_affinity(style, card_name):
        if style == "Mountain" and card_name == TSURIOTOSHI:
            return 7  # the new second finisher belongs in Mountain's top three
        return old_affinity(style, card_name)
    style_ai_v5.card_affinity = mountain_affinity
    _installed = True
