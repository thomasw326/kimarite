"""Seeded Sumo Style starter and exclusion selections (experimental V5)."""
import random
from dataclasses import dataclass
from .catalog import CARD_POOL
from .exclusions import GAIN_OR_ESTABLISH_GRIP, REQUIRES_GRIP, UNIVERSALLY_PROTECTED_IDS
from .models import FighterState, Wrestler, Stat
from .styles_v5 import STYLES, preference_bonus, resolve_card


@dataclass(frozen=True)
class StyleBuild:
    fighter: FighterState
    excluded_ids: frozenset[int]


def build_style(style: str, seed: int = 0, ranking: int = 1, difficulty: int = 0) -> StyleBuild:
    profile = STYLES[style]
    rng = random.Random(seed)
    kimarite = resolve_card(rng.choices(profile.starting_kimarite, weights=[2, 1])[0])
    basics = list({c.name: c for c in reversed(CARD_POOL) if not c.is_kimarite}.values())

    def pick(options):
        return rng.choices(options, weights=[1 + 3 * preference_bonus(profile, c.name) for c in options])[0]

    tachiai = pick(basics)
    top = pick([c for c in basics if c.name != tachiai.name])
    reserved = {kimarite.name, tachiai.name, top.name}
    eligible = [
        c for c in CARD_POOL
        if c.name not in reserved and c.card_id not in UNIVERSALLY_PROTECTED_IDS
    ]
    needs_grip = kimarite.name in REQUIRES_GRIP
    eligible.sort(key=lambda c: (
        needs_grip and c.name in GAIN_OR_ESTABLISH_GRIP,
        preference_bonus(profile, c.name), c.card_id,
    ))
    count = max(0, min(len(eligible), 7 + difficulty))
    excluded = frozenset(c.card_id for c in eligible[:count])
    remainder = [c for c in CARD_POOL if c.name not in reserved and c.card_id not in excluded]
    rng.shuffle(remainder)
    third = next((s for s in Stat if s.value not in {profile.primary, profile.secondary}), Stat(profile.primary))
    wrestler = Wrestler(
        style, *profile.stats, kimarite, tachiai, top,
        primary=Stat(profile.primary), secondary=Stat(profile.secondary),
        tertiary=third, ranking=ranking,
    )
    return StyleBuild(
        FighterState(wrestler, draw_pile=[top, *remainder, tachiai], kimarite_zone=[kimarite]),
        excluded,
    )
