# Kimarite

Kimarite is a sumo management roguelike and tactical card game. The next milestone is **playable human-vs-AI sumo**, supported by a single deterministic rules engine that can also run AI-vs-AI simulations for balance testing.

## Current goal: playable engine and 15-style AI

- Support both human and AI controllers using the same legal actions, state transitions, and win conditions.
- Separate the **game engine** (rules, card resolution, hidden information, state) from **decision controllers** (human input or AI choices).
- Allow the engine to pause for player decisions, including card selection, targets, and optional effects, then resume consistently.
- Preserve reproducible bout seeds, event logs, and sufficient state for saved/resumed player matches.
- Build 15 recognizable AI opponents, one for each Sumo Style. Give each weighted preferences for its top three Kimarite and top seven other cards from the Google Sheets affinity library.
- At difficulty 0, exclude seven eligible cards from the AI draw pile, using low affinity and strategic mismatch rather than the old wrestler-name-specific rules; preserve protected starting cards and key setup cards.
- In combat, choose an immediate win first, prevent an immediate loss, and treat Position or Momentum of -2 or worse as danger. Pursue negative-Momentum win conditions only with a credible near-term finish; otherwise use current state and legal options before style affinity.
- Keep Technique's first-turn card-access rewards unchanged pending validation. Verify intended Grip-based defensive/Power-exhaustion protection and measure early losses before considering additional Technique bonuses.
- Retain deck exhaustion as a loss condition, but do not optimize the AI around this historically rare outcome.

## Development approach

1. **Shared game engine** — deterministic rules, legal actions, hidden information, interactive decision points, save/resume state.
2. **Human and AI controllers** — same interface for human choices, existing tactical AI, and the new 15-style AI.
3. **Playtesting and analysis** — scripted human-vs-AI tests and seeded AI-vs-AI comparisons, followed by larger balance runs.

The active Google Doc and Google Sheets card library / Sumo Styles affinity worksheets are the design sources of truth. This README describes the next development direction; it does not assert that the new AI or human-facing interface has been implemented. Existing experimental pull requests and rules require reconciliation before declaring the playable milestone complete.
