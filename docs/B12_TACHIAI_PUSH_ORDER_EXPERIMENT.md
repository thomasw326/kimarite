# B12 Tachiai Push-order correction — experimental ruleset

This branch changes opening resolution **only**. The 7,080-bout B12 baseline was run with the old engine and must not be relabelled as a test of these rules. Main game remains untouched pending balance-review approval.

## Approved intended resolution

1. Establish the opening comparisons using base stats, committed cards and revealed orbs (Power 🟣 / Technique 🟢 / Spirit 🟠). Initialise persistent Power once, then apply Tachiai card-specific Power modifiers (e.g. Nodowa, Hold Position, Harite).
1a. For Oshi/Tsuki prepared reveal chains, add revealed Power orbs to both the comparison and persistent fighter Power. Otherwise these orbs would fail to block Push.\n2. Calculate **Spirit-generated Push** at the existing Spirit-difference 1, 4, 7, ... thresholds. Apply dedicated anti-Spirit-Push effects from Hold Position, Immovable, Sidestep and Give Ground to this Spirit component.
3. Add **all prepared-card bonus Push** (Explosive Step, Shove, Stare Down, Get Underneath, sacrificed Headlong Charge, etc.). Net opposite-facing Push from the two sides.
4. Determine the defender against the direction of net Push. Block **one Push per point by which the defender's effective Power exceeds the attacker's effective Power**. Do not double-count the Power comparison; Power is not converted into Push.
5. Apply the resulting Push **once**; if it exceeds ring boundaries, win immediately via ring-out.
6. Keep ordinary remaining Tachiai effects, Momentum, Technique access, prepared card destinations and first actor rules as before.

**Old implementation issues:** Spirit Push was blocked before card bonuses; bonus Push ignored Power resistance; additionally the Power comparison advantage was included a second time on top of already initialised persistent Power, exaggerating Spirit-only Push blocking.

Examples:
- Spirit advantage +4 => 2 Push, prepared Explosive Step => +1 Push, opposing effective Power advantage +2 => **1 net Push**.
- Tied Spirit, prepared Shove => +1 Push, opposing Power advantage +1 => **0 net Push**.
- Spirit advantage +7 => 3 Push, opposing Power advantage +2 => **1 net Push**.

Source: `src/kimarite/tachiai.py` and `src/kimarite/tachiai_effects.py`. Regression: `tests/test_b12_tachiai_push_order.py`. No deck/card orb values are altered. A new B12 run is needed before making balance judgements from new-rule results.
