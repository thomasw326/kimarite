"""Conservative B10 UI text registry.

Only audited descriptions are presented as rules. This module does not alter game
mechanics. Glossary entries are independent of card-specific rules.
"""
CARD_TEXT = {
    "Katasukashi": {"timing": "Kimarite", "effect": "Win if the opponent has no Grip, your Momentum is at least +2, and you have at least four more cards in hand than the opponent.", "status": "verified"},
    "Pull": {"timing": "Exchange", "effect": "Lose 1 Position. Gain 1 Momentum. Make the opponent Unstable. Draw 1 card, then discard 1 card from your hand.", "status": "verified"},
    "Give Ground": {"timing": "Exchange", "effect": "Lose 1 Position. Gain 1 Momentum and 1 Power. Draw 1 card.", "status": "verified"},
    "Okuritaoshi": {"timing": "Generated Kimarite", "effect": "Win if your Power is at least 8 and your Momentum is at least +1.", "status": "verified"},
}
GLOSSARY = {
    "Position": "Your location relative to the opponent and the tawara. Positive values favour your side; reaching the ring-out boundary ends the bout.",
    "Momentum": "A signed measure of which wrestler is driving the exchange. Card effects and Kimarite can require relative Momentum.",
    "Power": "Your current physical strength during the bout. Some Kimarite and effects check this value.",
    "Grip": "Left or right belt control. Each side can be absent, established, or deep.",
    "Unstable": "A vulnerable state applied by card effects. It can affect subsequent actions and finishing conditions.",
    "Kimarite": "A victory technique placed in the Kimarite Zone. It wins when its requirements are satisfied.",
    "Temporary": "An ongoing card effect in the Temporary Zone. Its expiry or disruption depends on its specific rule.",
    "Tachiai": "The opening clash before Exchange turns.",
    "Exchange": "The alternating turns in which wrestlers play cards and attempt to win.",
    "Push": "Ring movement caused by a card or the opening clash; separate from Momentum.",
    "Draw": "Move a card from your draw pile into your hand according to the current effect.",
    "Discard": "Move a card from your hand to the discard pile.",
}
def card_info(card):
    entry = CARD_TEXT.get(card.name, {})
    return {
        "name": card.name, "id": card.card_id,
        "power": card.power, "technique": card.technique, "spirit": card.spirit,
        "is_kimarite": card.is_kimarite,
        "timing": entry.get("timing", "Kimarite" if card.is_kimarite else "Exchange / Tachiai (unverified)"),
        "description": entry.get("effect", ""),
        "description_status": entry.get("status", "needs_audit"),
    }
