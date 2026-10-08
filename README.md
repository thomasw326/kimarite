# Kimarite

Kimarite is a sumo-inspired tactical card game currently being developed as a deterministic rules engine and AI-vs-AI simulator.

## Current goal

The first implementation milestone is a headless simulator that can:

- resolve a bout deterministically from seeds,
- run AI-vs-AI matches,
- emit a complete event log for debugging,
- batch thousands of matches for balance analysis.

Player-facing UI will come later.

## Development approach

The codebase is split conceptually into:

1. **Game engine** — rules and state transitions.
2. **AI** — decisions made from legal game states.
3. **Simulation / analysis** — batch runs and balance statistics.

The tabletop rules and card library remain the design source of truth while the engine is being validated.
