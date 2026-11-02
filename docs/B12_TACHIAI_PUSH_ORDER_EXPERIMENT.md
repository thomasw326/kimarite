# B12 Tachiai Push-order correction — experimental ruleset

This branch changes opening resolution **only**. The 7,080-bout B12 baseline was run with the old engine and must not be relabelled as a test of these rules. Main game remains untouched pending balance-review approval.

## Intended resolution — Power thresholds unchanged

1. Establish the opening comparisons using base stats, committed cards and revealed orbs (Power 🟣 / Technique 🟢 / Spirit 🟠). Initialise persistent Power once, then apply Tachiai card-specific Power modifiers (e.g. Nodowa, Hold Position, Harite).
1a. For Oshi/Tsuki prepared reveal chains, add revealed Power orbs to both the comparison and persistent fighter Power. Otherwise these orbs would fail to block Push.
2. Calculate **Spirit-generated Push** at the existing Spirit-difference 1, 4, 7, ... thresholds. Apply dedicated anti-Spirit-Push effects from Hold Position, Immovable, Sidestep and Give Ground to this Spirit component.
3. Add **all prepared-card bonus Push** (Explosive Step, Shove, Stare Down, Get Underneath, sacrificed Headlong Charge, etc.). Net opposite-facing Push from the two sides.
4. Determine the defender against the direction of net Push. Block Push using the **original Power-advantage thresholds**: 1–3 Power lead = 1 block, 4–6 = 2, 7–9 = 3, 10–12 = 4, and so on. Power is not converted into Push, and its comparison must not be counted twice.
5. Apply the resulting Push **once**; if it exceeds ring boundaries, win immediately via ring-out.
6. Keep ordinary remaining Tachiai effects, Momentum, Technique access, prepared card destinations and first actor rules as before.

**Old implementation issues:** Spirit Push was blocked before card bonuses; bonus Push ignored Power resistance; additionally the Power comparison advantage was included a second time on top of already initialised persistent Power, exaggerating Spirit-only Push blocking. **The 1/4/7/10 Power-blocking thresholds are deliberately preserved, not changed to one-for-one.**

Examples:
- Spirit advantage +4 => 2 Push, prepared Explosive Step => +1 Push, opposing effective Power advantage +2 => **2 net Push** (1 block).
- Tied Spirit, prepared Shove => +1 Push, opposing Power advantage +1 => **0 net Push**.
- Spirit advantage +7 => 3 Push, opposing Power advantage +2 => **2 net Push** (1 block).

Source: `src/kimarite/tachiai.py` and `src/kimarite/tachiai_effects.py`. Regression: `tests/test_b12_tachiai_push_order.py`. No deck/card orb values are altered. A new B12 run is needed before making balance judgements from new-rule results.
