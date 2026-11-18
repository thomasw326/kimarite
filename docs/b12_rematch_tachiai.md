# B12 rematch Tachiai

In the six-basho campaign, the player earns a top-card choice when their
most recent bout against the scheduled wrestler was a loss. The eligibility
lookup uses the wrestler's stable ID and saved results across basho. Older
saves that stored only the opponent's name use the unique, stable name inside
that campaign. A win in a later meeting clears eligibility until another loss.

The player commits zero to three of their own cards first. The game then
shows the opponent's three seeded opening cards: starting Kimarite, prepared
Tachiai, and original draw-pile top. Choosing one locks the decision and starts
the usual Tachiai resolver, including any effects that reveal, mill, or shuffle
the top card. The original top needs no change. Choosing either other card
places a bout-only physical copy on top so the original still serves its
starting-zone or prepared-effect role. The copy can be used normally during
the bout and is discarded with the session at bout end.

The browser keeps the commitment and choice in its existing action journal.
The same seed and commands reproduce the offer and live opening during recovery.
The normal B11 and B12 non-rematch flow proceeds directly from commitment to
resolution. The B12 ranked AI-vs-AI setup uses its existing path.

Implementation spans B12 campaign pairing, pending and live opening sessions,
HTTP snapshots and action handling, and the browser Dohyō. The campaign HTTP
tests exercise hidden pre-commit state, all three choices, physical card
placement, rejected changes, retries, and deterministic replay.
