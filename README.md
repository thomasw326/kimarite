# Kimarite

Kimarite is a sumo-inspired tactical card game with a deterministic rules engine, AI-vs-AI simulator, and an early **V5.0 human-vs-AI terminal prototype**.

## Play a bout (V5.0 development branch)

From the repository root:

```powershell
python -m pip install -e ".[dev]"
python -m kimarite.play_human --human Fujinokawa --opponent Fujinokawa
```

Choose cards to keep when the Technique or Grip card-access prompt appears. During your Exchange turn, enter the numbered card you want to play, `pass` to end the turn, or `quit` to leave. Some card effects prompt for extra choices. You can also choose a different opponent and AI mode:

```powershell
python -m kimarite.play_human --human Fujinokawa --opponent Tochinoshin --ai-mode personality --seed 42
```

**Prototype limits:** This is terminal-only, not a graphical game; it uses the existing predefined wrestler templates rather than the upcoming 15 weighted style archetypes. The engine's AI operates on full game state internally; the public observation API only exposes the player's own hand and public opponent information. There is no persistent save/load interface yet.

## Developer tests

```powershell
python -m pytest -q
```

The rules engine remains shared across tactical AI, personality AI, automated simulation, and human actions. Human card and keep/bottom choices use transactional execution so invalid input does not corrupt the bout state.

## Experimental 15-style AI\n\nThe V5 branch also contains all 15 Sumo Styles from the live card-library sheet. The new builder selects favored starting cards with weighted randomness, excludes seven eligible low-affinity cards at base difficulty, and preserves required Grip setup. The style AI prioritizes wins and recovery from dangerous Position/Momentum before its favorite cards. These modules are **opt-in** and do not replace the existing 30-wrestler balance fixtures.\n\nPlay **as one Sumo Style against another** in the terminal prototype:

```powershell
python -m kimarite.play_human --human-style "Mountain" --opponent-style "The Technician"
```

The existing named-wrestler mode remains supported. This new AI is still experimental, and an initial winning opening can end a bout before interactive card selection.

Run a mirrored 15-style test locally (210 bouts per repetition):\n\n```powershell\npython -m kimarite.style_round_robin_v5 --repetitions 1\n```\n\n## Current development roadmap

1. Complete and validate the human-vs-AI bout lifecycle.
2. Validate the new 15 style-aware AI opponents and improve their decision priorities.
3. Add survival-first AI priorities for dangerous Position and Momentum.
4. Compare deterministic AI-vs-AI runs for balance without changing approved card rules unnecessarily.

The tabletop rules and card library remain the design source of truth; gameplay changes are validated separately from controller and UI development.
