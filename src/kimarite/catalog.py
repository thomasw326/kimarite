from __future__ import annotations

from dataclasses import dataclass

from .models import Card, Stat, Wrestler


# V5 current print-pool orbs; stable historical IDs retained for reproducibility.
CARD_POOL: tuple[Card, ...] = (
    Card(1, "Oshi", 0, 0, 1),
    Card(3, "Tsuki", 1, 0, 0),
    Card(5, "Tsuppari", 2, 0, 1),
    Card(7, "Headlong Charge", 0, 0, 3),
    Card(8, "Nodowa", 3, 0, 0),
    Card(9, "Harite", 3, 0, 1),
    Card(10, "Gain Left Grip", 0, 3, 0),
    Card(11, "Gain Right Grip", 0, 3, 0),
    Card(12, "Uwate", 0, 3, 0),
    Card(13, "Shitate", 0, 3, 0),
    Card(14, "Attempt Two-Handed Grip", 0, 3, 1),
    Card(15, "Attempt Deep Outside Grip", 0, 3, 1),
    Card(16, "Attempt Deep Inside Grip", 0, 3, 1),
    Card(17, "Shiko Stomp", 1, 1, 1),
    Card(18, "Salt Throw", 1, 1, 3),
    Card(19, "Stare Down", 1, 1, 1),
    Card(20, "Power Water", 1, 2, 2),
    Card(21, "Belt Slap", 2, 0, 3),
    Card(22, "Tsuri", 2, 2, 0),
    Card(23, "Yori", 1, 2, 1),
    Card(24, "Gaburi", 1, 2, 1),
    Card(25, "Ottsuke", 1, 2, 1),
    Card(26, "Hold Position", 3, 0, 0),
    Card(27, "Immovable", 3, 0, 0),
    Card(28, "Henka", 0, 4, 0),
    Card(29, "Pull", 0, 1, 2),
    Card(30, "Get Underneath", 1, 1, 0),
    Card(31, "Read the Move", 0, 2, 1),
    Card(32, "Reset to Neutral", 0, 2, 1),
    Card(33, "Regain Balance", 2, 0, 2),
    Card(34, "Sidestep", 0, 3, 0),
    Card(35, "Use the Tawara", 0, 3, 0),
    Card(36, "Kannuki", 2, 1, 0),
    Card(37, "Morozashi", 0, 3, 0),
    Card(38, "Yorikiri", 1, 1, 1, True),
    Card(39, "Oshidashi", 2, 0, 1, True),
    Card(40, "Tsukidashi", 1, 0, 2, True),
    Card(41, "Oshitaoshi", 3, 0, 0, True),
    Card(42, "Yoritaoshi", 2, 1, 0, True),
    Card(43, "Give Ground", 0, 2, 1),
    Card(44, "Uwatenage", 0, 2, 1, True),
    Card(45, "Hatakikomi", 1, 0, 2, True),
    # Big Test 2: include the eight starting-only Kimarite in every deck role.
    Card(46, "Katasukashi", 0, 3, 0, True),
    Card(47, "Hikiotoshi", 0, 1, 2, True),
    Card(48, "Tottari", 1, 1, 0, True),
    Card(49, "Tsukiotoshi", 1, 1, 1, True),
    Card(50, "Tsukitaoshi", 1, 0, 2, True),
    Card(51, "Tsuridashi", 2, 1, 0, True),
    Card(52, "Kotenage", 1, 1, 0, True),
    Card(53, "Abisetaoshi", 3, 0, 0, True),
    Card(54, "Shove", 2, 0, 0),
    Card(55, "Explosive Step — Fumikomi", 0, 0, 3),
    Card(58, "Shitatenage", 0, 2, 1, True),
    Card(59, "Kirikaeshi", 0, 2, 1, True),
    Card(60, "Okuridashi", 0, 1, 2, True),
    Card(61, "Okuritaoshi", 1, 0, 2, True),
    Card(62, "Sukuinage", 1, 1, 1, True),
    Card(63, "Utchari", 0, 2, 0, True),
    Card(64, "Uwatedashinage", 0, 2, 1, True),
)


# Starting Kimarite are game definitions, not necessarily present in the
# current 45-card shuffled pool snapshot. Synthetic IDs are engine-only.
STARTING_KIMARITE: tuple[Card, ...] = (
    Card(1001, "Katasukashi", 0, 3, 0, True),
    Card(1002, "Hikiotoshi", 0, 1, 2, True),
    Card(1003, "Tottari", 1, 1, 0, True),
    Card(1004, "Yorikiri", 1, 1, 1, True),
    Card(1005, "Uwatenage", 0, 2, 1, True),
    Card(1006, "Hatakikomi", 1, 0, 2, True),
    Card(1007, "Tsukiotoshi", 1, 1, 1, True),
    Card(1008, "Tsukitaoshi", 1, 0, 2, True),
    Card(1009, "Oshidashi", 2, 0, 1, True),
    Card(1010, "Oshitaoshi", 3, 0, 0, True),
    Card(1011, "Tsuridashi", 2, 1, 0, True),
    Card(1012, "Kotenage", 1, 1, 0, True),
    Card(1013, "Abisetaoshi", 3, 0, 0, True),
    Card(1014, "Yoritaoshi", 2, 1, 0, True),
    Card(1015, "Tsukidashi", 1, 0, 2, True),
    Card(1016, "Shitatenage", 0, 2, 1, True),
    Card(1017, "Kirikaeshi", 0, 2, 1, True),
    Card(1018, "Okuridashi", 0, 1, 2, True),
    Card(1019, "Okuritaoshi", 1, 0, 2, True),
    Card(1020, "Sukuinage", 1, 1, 1, True),
    Card(1021, "Utchari", 0, 2, 0, True),
    Card(1022, "Uwatedashinage", 0, 2, 1, True),
)


def card_by_id(card_id: int) -> Card:
    for card in (*CARD_POOL, *STARTING_KIMARITE):
        if card.card_id == card_id:
            return card
    raise KeyError(card_id)


def card_by_name(name: str, *, prefer_starting_kimarite: bool = False) -> Card:
    groups = (
        (STARTING_KIMARITE, CARD_POOL)
        if prefer_starting_kimarite
        else (CARD_POOL, STARTING_KIMARITE)
    )
    for group in groups:
        for card in group:
            if card.name == name:
                return card
    raise KeyError(name)


@dataclass(frozen=True)
class WrestlerTemplate:
    name: str
    primary: Stat
    secondary: Stat
    tertiary: Stat
    base_power: int
    base_technique: int
    base_spirit: int
    starting_kimarite: str
    prepared_tachiai_card: str
    top_of_deck_card: str
    exclusion_note: str

    def build(self, ranking: int | None = None) -> Wrestler:
        return Wrestler(
            name=self.name,
            base_power=self.base_power,
            base_technique=self.base_technique,
            base_spirit=self.base_spirit,
            starting_kimarite=card_by_name(
                self.starting_kimarite,
                prefer_starting_kimarite=True,
            ),
            prepared_tachiai_card=card_by_name(self.prepared_tachiai_card),
            top_of_deck_card=card_by_name(self.top_of_deck_card),
            primary=self.primary,
            secondary=self.secondary,
            tertiary=self.tertiary,
            ranking=ranking,
        )


ORIGINAL_WRESTLERS: dict[str, WrestlerTemplate] = {
    "Ura": WrestlerTemplate("Ura", Stat.TECHNIQUE, Stat.TECHNIQUE, Stat.POWER, 0, 5, 1, "Katasukashi", "Salt Throw", "Use the Tawara", "Power/comparison, Spirit comparison, Power threshold."),
    "Oshoma": WrestlerTemplate("Oshoma", Stat.TECHNIQUE, Stat.SPIRIT, Stat.POWER, 1, 3, 2, "Hikiotoshi", "Get Underneath", "Pull", "Multiple Push, Push+Power, other Push."),
    "Asakoryu": WrestlerTemplate("Asakoryu", Stat.TECHNIQUE, Stat.SPIRIT, Stat.POWER, 0, 3, 3, "Tottari", "Power Water", "Ottsuke", "Provide Grip, Power comparisons, Power thresholds."),
    "Wakamotoharu": WrestlerTemplate("Wakamotoharu", Stat.TECHNIQUE, Stat.POWER, Stat.SPIRIT, 2, 4, 0, "Yorikiri", "Gain Left Grip", "Yori", "Spirit comparisons, remove Grip, high Spirit orbs."),
    "Hoshoryu": WrestlerTemplate("Hoshoryu", Stat.TECHNIQUE, Stat.POWER, Stat.SPIRIT, 2, 3, 1, "Uwatenage", "Shiko Stomp", "Attempt Deep Outside Grip", "Remove Grip, require negative, downside gamble."),
    "Abi": WrestlerTemplate("Abi", Stat.SPIRIT, Stat.TECHNIQUE, Stat.POWER, 1, 2, 3, "Hatakikomi", "Henka", "Kannuki", "No-Spirit cards, highest Push first."),
    "Tobizaru": WrestlerTemplate("Tobizaru", Stat.SPIRIT, Stat.TECHNIQUE, Stat.POWER, 0, 2, 4, "Tsukiotoshi", "Give Ground", "Sidestep", "Power comparison, Power threshold, provide Power."),
    "Fujinokawa": WrestlerTemplate("Fujinokawa", Stat.SPIRIT, Stat.SPIRIT, Stat.TECHNIQUE, 1, 0, 5, "Tsukitaoshi", "Stare Down", "Oshi", "Lose Position, lose Momentum, require Grip."),
    "Houdan": WrestlerTemplate("Houdan", Stat.SPIRIT, Stat.POWER, Stat.TECHNIQUE, 3, 0, 3, "Oshidashi", "Headlong Charge", "Read the Move", "Require Grip, establish Grip, highest Technique orbs."),
    "Takanosho": WrestlerTemplate("Takanosho", Stat.SPIRIT, Stat.POWER, Stat.TECHNIQUE, 2, 1, 3, "Oshitaoshi", "Nodowa", "Regain Balance", "No draw/additional Play; then Grip; then least Power."),
    "Tochinoshin": WrestlerTemplate("Tochinoshin", Stat.POWER, Stat.TECHNIQUE, Stat.SPIRIT, 3, 3, 0, "Tsuridashi", "Gain Right Grip", "Morozashi", "Spirit-care; among non-Grip/non-Push, fewest Technique+Power."),
    "Tamawashi": WrestlerTemplate("Tamawashi", Stat.POWER, Stat.TECHNIQUE, Stat.SPIRIT, 3, 2, 1, "Kotenage", "Hold Position", "Tsuki", "Lose Position/Momentum; neither Power nor Grip disruption; fewest Power+Technique."),
    "Daieisho": WrestlerTemplate("Daieisho", Stat.POWER, Stat.SPIRIT, Stat.TECHNIQUE, 3, 1, 2, "Tsukidashi", "Harite", "Tsuppari", "Require Grip; establish Grip; fewest Power+Spirit."),
    "Shishi": WrestlerTemplate("Shishi", Stat.POWER, Stat.SPIRIT, Stat.TECHNIQUE, 4, 0, 2, "Abisetaoshi", "Belt Slap", "Attempt Two-Handed Grip", "Protect Grip-building; then Technique-orb cards, fewest Power+Spirit."),
    "Kotozakura": WrestlerTemplate("Kotozakura", Stat.POWER, Stat.POWER, Stat.SPIRIT, 5, 1, 0, "Yoritaoshi", "Immovable", "Attempt Deep Inside Grip", "Neither Power nor Grip utility; then fewest Power; Technique tie-break."),
}


ADDITIONAL_WRESTLERS: dict[str, WrestlerTemplate] = {
    "Arashigane": WrestlerTemplate("Arashigane", Stat.POWER, Stat.SPIRIT, Stat.TECHNIQUE, 4, 0, 2, "Oshidashi", "Headlong Charge", "Tsuppari", ""),
    "Aonami": WrestlerTemplate("Aonami", Stat.TECHNIQUE, Stat.POWER, Stat.SPIRIT, 2, 4, 0, "Yorikiri", "Gain Left Grip", "Morozashi", ""),
    "Hoshikaze": WrestlerTemplate("Hoshikaze", Stat.SPIRIT, Stat.SPIRIT, Stat.TECHNIQUE, 1, 0, 5, "Tsukitaoshi", "Stare Down", "Read the Move", ""),
    "Iwagane": WrestlerTemplate("Iwagane", Stat.POWER, Stat.TECHNIQUE, Stat.SPIRIT, 3, 2, 1, "Kotenage", "Hold Position", "Kannuki", ""),
    "Mizuhane": WrestlerTemplate("Mizuhane", Stat.TECHNIQUE, Stat.SPIRIT, Stat.POWER, 1, 3, 2, "Tsukiotoshi", "Salt Throw", "Power Water", ""),
    "Onosato": WrestlerTemplate("Onosato", Stat.POWER, Stat.TECHNIQUE, Stat.SPIRIT, 3, 3, 0, "Yorikiri", "Nodowa", "Yori", ""),
    "Aonishiki": WrestlerTemplate("Aonishiki", Stat.TECHNIQUE, Stat.POWER, Stat.SPIRIT, 2, 4, 0, "Yoritaoshi", "Gain Right Grip", "Yori", ""),
    "Kirishima": WrestlerTemplate("Kirishima", Stat.TECHNIQUE, Stat.POWER, Stat.SPIRIT, 2, 3, 1, "Uwatenage", "Gain Left Grip", "Uwate", ""),
    "Atamifuji": WrestlerTemplate("Atamifuji", Stat.POWER, Stat.SPIRIT, Stat.TECHNIQUE, 4, 0, 2, "Oshidashi", "Immovable", "Regain Balance", ""),
    "Takerufuji": WrestlerTemplate("Takerufuji", Stat.POWER, Stat.SPIRIT, Stat.TECHNIQUE, 3, 1, 2, "Oshidashi", "Tsuppari", "Ottsuke", ""),
}

PLAYTEST_WRESTLERS: dict[str, WrestlerTemplate] = {
    **ORIGINAL_WRESTLERS,
    **ADDITIONAL_WRESTLERS,
}
