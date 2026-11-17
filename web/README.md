# Kimarite browser UI

This directory contains the current **draft-first B12 browser playtest**. The rules engine remains in Python, served by `python -m kimarite.b10_web`.

## Two game locations

- **Heya (stable):** Create a named wrestler, assign the simple 2/1/0 Power/Technique/Spirit starting stats, draft a 28-card deck, plan each three-bout block, choose card-duplication rewards, and see tournament/year records.
- **Dohyō (ring):** Commit the player's hidden Tachiai choice, play the Exchange, monitor the Position and Momentum tracks, and view the bout result before returning to the Heya.

The initial campaign supports up to **six 15-bout tournaments**. Each subsequent tournament is redrafted to 28 starting from only the prior tournament's chosen duplication rewards (0–12 inherited cards).

In each three-bout block, **assign all nine physical opening cards up front**. Once a bout starts, its three selected cards are committed and cannot be changed or reused. After Bout 1, the two upcoming bouts remain editable and cards can be swapped directly between them; after Bout 2, only Bout 3 remains editable. Completed allocations are restored from the saved result when resuming an older tournament.

The **How to play** button reopens an introductory guide and basic sumo glossary. The first-visit guide is not shown over a saved draft, tournament or active bout.

## Development and testing

From the repository root:

```sh
python -m pip install -e ".[dev]"
python -m kimarite.b10_web
```

Open the local URL printed by the server. The source is `web/index.html`, `web/style.css` and `web/client.js`. The optional preset-wrestler test interface remains under **Developer practice options**, but the standard player experience does not require a preset wrestler.

Run `pytest -q` for the full suite, which includes onboarding guide, draft rollover, six-tournament-year state and UI phase contract tests. The public preview has an HTTP smoke workflow in `.github/workflows/staging-http-smoke.yml`. That check is not a substitute for manual desktop/mobile browser playtesting.

## Known release gaps

- The ring visual correctly follows the shared Position value from −4 to +4 and flags ring-edge danger, but does not yet animate a full ring-out.
- Card targeting, selection, layout and mobile responsiveness still need cross-device playtesting.
- The Python HTTP server is a limited single-instance prototype, not production multi-tenant infrastructure. A browser stores its own save/journal locally.
- The introductory guide is not yet a fully interactive guided tutorial.

For the active release tracker, see the [itch.io release roadmap](https://docs.google.com/spreadsheets/d/1YCAG7skE06kPsjadfWr_L7CYDCK_G2HJ68GcvadZcLk/edit).
