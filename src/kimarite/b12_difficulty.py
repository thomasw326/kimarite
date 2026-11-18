"""Private B12 rank-based AI-vs-AI difficulty and deck tuning.

Only NPC-versus-NPC bouts use this scale. The human-facing opponent-selection,
chosen 28-card deck, current-W/L duplicate rewards and six-basho ranking
rules are deliberately left unchanged.

Each rank band is a triangular/pyramid tier: 1; 2-3; 4-6; ...; 37-42.
The fixed +2..-2 personality variation is deterministic per world seed and
stable wrestler identity, not generated every turn, day or tournament.

Keep the 28+12 physical-deck model and the curated framework identity:
- protect the starting Kimarite and all 12 predetermined reward originals;
- change at most five *other* non-Kimarite cards, swapping low-affinity cards
  for high-affinity ones at positive difficulty (reverse at negative);
- preserve exactly 28 distinct initial cards and all 12 duplicate targets;
- add the optional established seven-step style-priority stat boosts.

No difficulty fields enter the public wrestler roster, banzuke or previews.
"""
from __future__ import annotations

from hashlib import sha256

from .affinity_v5 import affinity
from .b11_player_draft import AVAILABLE
from .stat_boosts import boosted_stats

MAX_RANK = 42
MAX_TIER = 9
DIFFICULTY_VARIANCE = 2
MAX_CARD_SWAPS = 5


def pyramid_tier(rank: int) -> int:
    """1→1, 2–3→2, 4–6→3, ..., 37–42→9."""
    if type(rank) is not int or not 1 <= rank <= MAX_RANK:
        raise ValueError("B12 AI difficulty requires a rank from 1 through 42")
    tier = 1
    while rank > tier * (tier + 1) // 2:
        tier += 1
    return tier


def base_difficulty(rank: int) -> int:
    """Highest rank has baseline 8; the bottom tier has baseline 0."""
    return MAX_TIER - pyramid_tier(rank)


def hidden_variance(world_seed: int, wrestler_id: str) -> int:
    """Private reproducible −2..+2 modifier for one persistent AI identity."""
    if type(world_seed) is not int or not isinstance(wrestler_id, str) or not wrestler_id.startswith("ai-"):
        raise ValueError("Difficulty variance needs a valid world seed and AI identity")
    digest = sha256(f"b12-ranked-ai-v1:{world_seed}:{wrestler_id}".encode()).digest()
    return int.from_bytes(digest[:8], "big") % (2 * DIFFICULTY_VARIANCE + 1) - DIFFICULTY_VARIANCE


def ai_difficulty(world_seed: int, wrestler_id: str, rank: int) -> int:
    """Recompute rank tier after banzuke movement; preserve private identity variance."""
    return base_difficulty(rank) + hidden_variance(world_seed, wrestler_id)


def tuned_base_cards(framework: dict, difficulty: int) -> list[str]:
    """Conservatively improve/weaken only non-core *basics* using V5 affinities.

    The fixed framework's 12 reward-copy targets always remain in its base.
    Only strict affinity improvements/weakening count; never swap a card for
    an equal or worse affinity and never change its finisher count.
    """
    if type(difficulty) is not int:
        raise ValueError("Difficulty must be an integer")
    cards = list(framework["base"])
    if not difficulty:
        return cards
    protected = set(framework["duplicates"]) | {framework["starting_kimarite"]}
    if not protected <= set(cards):
        raise ValueError("A framework reward or starting Kimarite is missing")
    style = framework["style_proxy"]
    # Preserve every planned Kimarite and starting/reward copy; stay at 28.
    candidates_to_replace = [
        name for name in cards if name not in protected and not AVAILABLE[name].is_kimarite
    ]
    candidates_to_add = [
        name for name, card in AVAILABLE.items()
        if not card.is_kimarite and name not in cards
    ]
    better = difficulty > 0
    candidates_to_replace.sort(
        key=lambda name: (affinity(style, name), name), reverse=not better
    )
    candidates_to_add.sort(
        key=lambda name: (affinity(style, name), name), reverse=better
    )
    swaps = min(MAX_CARD_SWAPS, (abs(difficulty) + 1) // 2)
    for old, new in zip(candidates_to_replace[:swaps], candidates_to_add[:swaps]):
        # No sideways or harmful edits masquerading as increased difficulty.
        delta = affinity(style, new) - affinity(style, old)
        if (better and delta <= 0) or (not better and delta >= 0):
            break
        cards[cards.index(old)] = new
    if len(cards) != 28 or len(set(cards)) != 28 or not protected <= set(cards):
        raise ValueError("Difficulty tuning must retain the 28+12 deck design")
    return cards


def tuned_stats(profile, difficulty: int) -> tuple[int, int, int]:
    """Use the already approved seven-step optional stat distribution."""
    from .models import Stat
    priorities = [Stat(profile.primary), Stat(profile.secondary)]
    priorities += [stat for stat in (Stat.POWER, Stat.TECHNIQUE, Stat.SPIRIT)
                   if stat not in priorities]
    # Clamp here rather than relying on the optional legacy helper: negative
    # ranks must soften deck composition, NEVER subtract baseline stats.
    return boosted_stats(profile.stats, tuple(priorities[:3]), max(0, difficulty),
                         enabled=True)
