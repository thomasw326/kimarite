# Kimarite

Kimarite is a sumo-inspired tactical card game with a deterministic rules engine, automated balance simulations, and a browser-based **Human vs AI practice bout**.

## Current builds and change-control

- **Approved B10 balance baseline:** `311dec7de8a0e3ef30365eeb8f0b8cd832912a4f` on `main`. Treat card effects, orb counts, wrestler decks, overflow ring rules, and the B10 State 3 AI as frozen unless a balance change is explicitly approved.
- **Human vs AI UI work:** `feature/b10-human-ui-session`, [PR #48](https://github.com/thomasw326/kimarite/pull/48). UI documentation, readability, session recovery, and isolated bug fixes belong here. **Do not merge it into main without explicit approval.**
- Experimental V5 and historic round-robin programs are separate from the approved B10 game; do not use old V5 prototypes as a source of current B10 card wording.

## Play Human vs AI (browser practice bout)

Start the web service from the repository root:

```powershell
python -m pip install -e ".[dev]"
python -m kimarite.b10_web
```

Open the local address printed by the service. The hosted deployment of the development branch may be used if configured; deployments are distinct from merging to main.

### Before the bout

1. Choose your rikishi and opponent from the approved roster, or choose **Random Wrestler** for either/both. Each random selection resolves to an actual wrestler when the bout starts.
2. Choose **Fixed seed** (default `20261021`) for reproducibility, or **Random seed** for a fresh bout. The actual seed and matchup are retained for session replay.
3. Choose the starting Kimarite, prepared Tachiai and first draw card, or select automatic opening. **Random player wrestler uses automatic opening** because its eligible opening cards depend on the selected wrestler.

### During the bout

- Your hand cards can be inspected to see orb values and audited effects; selecting **Play this card** is a separate action.
- Drawing, keeping, discarding, targeting Temporaries, and sacrificing Kimarite use numbered, named choices. **Inspect** shows card rules without selecting it. Raw engine indexes remain zero-based internally.
- A card drawn immediately before a discard (e.g. **Pull**) must be included by name among the eligible discard choices. Hidden opponent hands are not exposed. A genuinely random opponent discard is resolved by the engine, not chosen by the player.
- **Kimarite** and **Temporary** cards are visible for both wrestlers. Temporary effects are explained **directly in the wrestler panel** and in the inspector: ongoing protection, start-of-turn payoff, expiration, and disruption penalties where applicable.
- Both public **Discard pile** counts are clickable; each list shows the discarded cards and allows inspection.
- You can end a turn early with confirmation if Plays remain. **Copy log** captures the bout event history and reproducibility information.
- The browser retains the session setup and accepted actions in session storage so it can attempt to rebuild a bout after a server restart.

**Important:** The illustrated dohyo is currently **static**: the wrestler markers do not follow Position or Momentum. The numerical Position/Momentum indicators are authoritative. A moving-ring visual, ring-edge danger treatment, and ring-out animation are proposed UI work, **not yet implemented**. Choice boxes may also feel cramped when there are many options on mobile; responsive spacing is pending polish.

### Grip and Temporary behaviour

The B10 engine gives **Gain Left Grip, Gain Right Grip, Uwate, and Shitate** a one-use defense against **1 incoming Push** while in their Temporary Zone. The card leaves when that protection is used, or expires at its owner's next turn if unused. Multiple such active cards can each absorb Push. This is not a vestigial Temporary effect.

**Use the Tawara** no longer creates a Temporary. Some other cards produce delayed payoffs (e.g. **Yori**, **Gaburi**, **Denshamichi**, **Morozashi**) or disruption penalties; read their current UI descriptions rather than historical spreadsheet text. The UI text is in `src/kimarite/b10_card_info.py`; the engine rules remain the authority.

## Three-bout management (development)

The browser now offers a **Three-bout management** panel alongside single-bout practice. Select one approved B10 wrestler deck and deal nine physical card copies reproducibly from that 40-card deck. To ensure each bout has a legal opening, the current prototype deals **three Kimarite and six ordinary cards**. Allocate all nine, without reuse, into three groups of three: one starting Kimarite, one prepared Tachiai and one first draw for each bout.

Start the series to play three Human vs AI bouts in order against **three distinct randomly chosen opponents**. Each bout uses the approved B10 rules and State 3 AI, with its own deterministic seed; match results are summarized as you progress. The allocation and series results are stored in browser session storage to help recover after a refresh.

**Interpretation to validate against the earliest spreadsheet rules:** The nine cards currently allocate *opening slots*, not permanently remove cards from the wrestler's deck for later bouts. This uses existing B10 opening validation; it is a first playable management implementation, not a claim that the historical spreadsheet specified the same drafting constraints.

## Developer tests

```powershell
python -m pytest -q
```

The focused browser session test runs under GitHub Actions as **B10 human UI session smoke**; broader `tests` workflow checks should also pass before accepting changes. See [PR #48](https://github.com/thomasw326/kimarite/pull/48) for live check status. A green UI smoke test alone does not approve card balance changes.

## Historical terminal and V5 tools

Older experiments remain in the codebase. For terminal prototypes:

```powershell
python -m kimarite.play_human --human Fujinokawa --opponent Tochinoshin --seed 42
```

For historical V5 style experimentation:

```powershell
python -m kimarite.play_human --human-style "Mountain" --opponent-style "The Technician"
python -m kimarite.style_round_robin_v5 --repetitions 1
```

These commands are **not** equivalent to playing the B10 browser baseline and should not be treated as its AI validation.

## Next UI milestone

Finish responsive multi-choice/discard-picker layout, make the ring reflect **Position** and **Momentum separately** (including overflow boundary), complete mobile regression playtesting, and prepare a Human vs AI release candidate **without changing B10 balance**.
