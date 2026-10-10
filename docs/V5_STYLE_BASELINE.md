# V5 style round-robin baseline

This is a measurement pass, **not approval for balance changes**.

## Reproduction

Run the automated `v5-style-probe` workflow on `feature/v5-integration-controller`, or run locally:

```bash
python -m kimarite.style_round_robin_v5 --repetitions 4 --max-turns 30 > style-probe.json
```

The 15-style mirrored probe runs 840 bouts. Save the JSON artifact and report all style win rates, matchup asymmetries, turn lengths and exhaustion outcomes where available. Record the tested commit SHA and card snapshot version when interpreting results. Do not compare rates against the historical pre-sync probe as though the card sets were identical.

## Current gating

- Latest reported full regression suite before this document: [tests #698](https://github.com/thomasw326/kimarite/actions/runs/38025471022), passed.
- **Search keyword:** automatically take the first/topmost card in Draw Pile order matching the requested category; do not present the full deck or a choice dialog.
- This probe's numbers are exploratory and cannot be treated as a verified new balance baseline until its artifact has been inspected.
- Do not change cards, stats, style construction, or balancing rules without designer approval.
- Keep V4.5 unchanged and PR #16 in draft.

## Results

Awaiting confirmed artifact; no win rates are asserted here.
