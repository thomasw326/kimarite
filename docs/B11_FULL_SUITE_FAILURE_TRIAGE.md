# Full-suite failure audit — B11 draft PR #49

CI run 40303100937: **338 passed / 70 failed**. B11 focused tests and UI smoke pass on their respective workflows. The below failures are not automatically marked obsolete; each needs comparison to its era's approved rules before adjusting any assertions or production mechanics. Do not suppress failures with unconditional xfail/skip.

## Historic Tachiai orbs/draw thresholds (7)

- `tests/test_big_test.py::test_technique_advantage_1_3_5_7_thresholds`
- `tests/test_setup.py::test_fujinokawa_tochinoshin_setup_matches_v44_tachiai_case`
- `tests/test_tachiai.py::test_technique_access_scaling`
- `tests/test_tachiai.py::test_harite_power_applies_before_spirit_push_resistance`
- `tests/test_turns.py::test_technique_advantage_six_looks_eight_and_keeps_five_on_first_turn`
- `tests/test_v44_tachiai.py::test_spirit_generates_push_and_power_defends`
- `tests/test_v44_tachiai.py::test_technique_card_access_new_thresholds`

## Historic card effects, AI and finishing conditions (37)

- `tests/test_effects.py::test_oshi_gains_push_and_play_and_draws`
- `tests/test_effects.py::test_tsuppari_chains_after_oshi`
- `tests/test_effects.py::test_regain_balance_recovers_negative_momentum`
- `tests/test_kimarite_audit_v5.py::test_kimarite_audit_reports_denominators_and_triggers`
- `tests/test_r20_variant_runtime.py::test_henka_survives_and_finishes_before_start_of_turn_check`
- `tests/test_rules.py::test_momentum_overflow_converts_to_push`
- `tests/test_rules.py::test_momentum_overflow_still_pushes`
- `tests/test_temporary.py::test_use_tawara_prevents_push_and_gains_momentum`
- `tests/test_v43_balance.py::test_oshi_push_play_draw`
- `tests/test_v43_new_cards.py::test_explosive_step_exchange_push_depends_on_preplay_momentum`
- `tests/test_v51_new_kimarite.py::test_kirikaeshi_needs_power_deficit_hand_advantage_and_successful_reversal`
- `tests/test_v51_new_kimarite.py::test_okuri_finishes_need_successful_reversal_and_distinct_position_momentum`
- `tests/test_v51_new_kimarite.py::test_sukuinage_needs_no_grip_momentum_two_and_three_extra_hand_cards`
- `tests/test_v51_new_kimarite.py::test_okuri_exchange_choices_have_opposite_tradeoffs`
- `tests/test_v51_new_kimarite.py::test_new_draw_and_grip_exchange_effects`
- `tests/test_v51_new_kimarite.py::test_normal_v51_surviving_reversal_sets_event_without_r20_flag`
- `tests/test_v51_new_kimarite.py::test_normal_v51_start_turn_can_win_with_completed_reversal`
- `tests/test_v5_actions.py::test_human_pull_prompts_for_mode_without_mutation`
- `tests/test_v5_ai_choice_policies.py::test_pull_ai_explores_both_printed_modes`
- `tests/test_v5_delayed_grip.py::test_yori_delayed_momentum_depends_on_grip_comparison`
- `tests/test_v5_human_uwate.py::test_human_uwate_requires_look_selection_and_rolls_back`
- `tests/test_v5_katasukashi_attribution.py::test_katasukashi_records_triggering_card`
- `tests/test_v5_katasukashi_position_only.py::test_katasukashi_requires_hand_advantage_and_opponent_no_grip`
- `tests/test_v5_morozashi_deep.py::test_morozashi_requires_exactly_one_gripping_hand[1-1]`
- `tests/test_v5_morozashi_deep.py::test_morozashi_requires_exactly_one_gripping_hand[2-1]`
- `tests/test_v5_oshi_tsuki_momentum.py::test_oshi_push_despite_negative_momentum`
- `tests/test_v5_pull_underneath_sync.py::test_pull_filter_mode_draws_then_discards_without_temporary`
- `tests/test_v5_pull_underneath_sync.py::test_pull_reverses_momentum_but_not_position`
- `tests/test_v5_pull_underneath_sync.py::test_tawara_search_takes_topmost_kimarite_not_first_card`
- `tests/test_v5_pull_underneath_sync.py::test_ai_tawara_search_defaults_to_first_eligible`
- `tests/test_v5_read_pull_choices.py::test_pull_filter_option_does_not_create_temporary`
- `tests/test_v5_read_pull_choices.py::test_pull_reversal_option_preserves_temporary`
- `tests/test_v5_shiko_playability.py::test_shiko_stomp_exchange_play_is_legal_and_persistent`
- `tests/test_v5_shiko_playability.py::test_shiko_stomp_visible_to_tactical_and_style_ai`
- `tests/test_v5_style_round_robin.py::test_slot_outcomes_reconcile_to_participants`
- `tests/test_v5_tottari_timing.py::test_tottari_start_check_preserves_prior_opponent_grip_event`
- `tests/test_v5_uwate_sync.py::test_uwate_deep_grip_plays_selected_card_free`

## Old difficulty/exclusion rules (17)

- `tests/test_exclusions.py::test_tochinoshin_difficulty_zero_follows_written_priority`
- `tests/test_v5_style_builds.py::test_style_build_is_deterministic_and_excludes_seven[Bulldozer]`
- `tests/test_v5_style_builds.py::test_style_build_is_deterministic_and_excludes_seven[Charger]`
- `tests/test_v5_style_builds.py::test_style_build_is_deterministic_and_excludes_seven[Disruptor]`
- `tests/test_v5_style_builds.py::test_style_build_is_deterministic_and_excludes_seven[Fast Grappler]`
- `tests/test_v5_style_builds.py::test_style_build_is_deterministic_and_excludes_seven[Heavy Hitter]`
- `tests/test_v5_style_builds.py::test_style_build_is_deterministic_and_excludes_seven[Mawashi Specialist]`
- `tests/test_v5_style_builds.py::test_style_build_is_deterministic_and_excludes_seven[Mountain]`
- `tests/test_v5_style_builds.py::test_style_build_is_deterministic_and_excludes_seven[Opportunist]`
- `tests/test_v5_style_builds.py::test_style_build_is_deterministic_and_excludes_seven[Power Grappler]`
- `tests/test_v5_style_builds.py::test_style_build_is_deterministic_and_excludes_seven[Pressure Fighter]`
- `tests/test_v5_style_builds.py::test_style_build_is_deterministic_and_excludes_seven[Speed Demon]`
- `tests/test_v5_style_builds.py::test_style_build_is_deterministic_and_excludes_seven[The Arsenal]`
- `tests/test_v5_style_builds.py::test_style_build_is_deterministic_and_excludes_seven[The Specialist]`
- `tests/test_v5_style_builds.py::test_style_build_is_deterministic_and_excludes_seven[The Technician]`
- `tests/test_v5_style_builds.py::test_style_build_is_deterministic_and_excludes_seven[Unorthodox Powerhouse]`
- `tests/test_v5_style_builds.py::test_style_difficulty_modifies_exclusion_count`

## Historic manifest/card print snapshots (9)

- `tests/test_r21_gauntlet.py::test_manifest_coverage_and_ids`
- `tests/test_r21_gauntlet.py::test_50_arm_schedule`
- `tests/test_v42_approved.py::test_approved_orbs_and_uncapped_power`
- `tests/test_v42_approved.py::test_approved_kinematic_finishes`
- `tests/test_v42_approved.py::test_regain_balance_conditional_power`
- `tests/test_v51_release.py::test_release_pool_exactly_matches_manifest`
- `tests/test_v51_release.py::test_release_catalog_orbs`
- `tests/test_v51_release.py::test_fifteen_styles_prune_seven_at_baseline_and_restore_at_negative_difficulty`
- `tests/test_v5_print_pool_sync.py::test_current_print_pool_orbs_match_snapshot`

## Resolution strategy

1. Verify each failing legacy expectation against the approved B11 baseline and versioned rule documents. A historical test may be archived with an explicit provenance note if superseded, but should not silently disappear.
2. Repair actual active-rule defects in source with narrow regression tests.
3. Keep full-suite workflow visible/red until its scope and historic compatibility contract are reviewed; the dedicated B11 workflow is the feature gate.
4. CI run 40303687016: focused B11 suite success. Do not claim the 70 have been fixed.

## Verified regression reduction — test isolation fix
- Root cause: `tests/test_b7_runtime_audit.py` invoked `r26_style_final22.install_final22()`, which mutates six process-global style builder/AI bindings (including `B6_FIXED_COMPOSITION_DECK=True`) but never restored them. Later V5 tests then ran the wrong experimental rule configuration.
- Confirmed by isolated V5 style-builder workflow (run 40305002575): **PASS** before changing gameplay source.
- Added an autouse teardown fixture *scoped to the B7 audit test module* that restores all six original bindings after each test. No core game rules or approved card values changed.
- Full-suite GitHub Actions run 40305193776 after fix: **51 failed / 357 passed** (previously 70 failed / 338 passed). **19 red tests resolved**, with no additional failures; focused B11 and B10 UI smoke workflows also passed.
- Remaining 51 failures need separate era-by-era rules validation; do not suppress by blanket skipping or alter approved B11 mechanics to satisfy obsolete assertions.

## Further red-test push (October 26)
- Added eight-way independent GitHub Actions matrix at `.github/workflows/b11-legacy-diagnostics.yml`, one historical red test per fresh Python process. This confirms many failures are true old-rule expectation mismatches rather than test-order contamination. The workflow is **diagnostic**, so it intentionally fails until those tests are reconciled.
- R21 gauntlet manifest has **63 arms, 22 Kimarite families**, verified by direct inspection of `data/r21_kimarite_arms.json`. Tests still asserted 50 arms/18 families despite the expanded manifest. Updated `tests/test_r21_gauntlet.py` to the current manifest shape and calculate schedule length from actual arm count; isolated manifest CI job succeeded.
- `tests/test_v5_style_round_robin.py` incorrectly equated *all planned card-slot appearances* with *completed-bout outcomes*. When a bout reaches its turn limit, an appearance still exists without a win or loss. Updated assertions to check `2 * planned_bouts` appearances vs `2 * completed` resolved outcomes, preserving non-negative unresolved counts.
- Focused B11 and B10 UI smoke checks succeeded on commit `112bfb8`. Full pytest re-run `40306744205` initiated, latest result should be checked before reporting a revised global failure count.
- No live gameplay rules, card orbs, approved balance, or B10 main changed.

## Additional verified reduction — Shiko and Morozashi
- Full suite after the approved B11 Shiko Stomp Exchange +1 Play test correction: **47 failed, 361 passed** (GitHub Actions run 40330264735).
- `tests/test_v5_shiko_playability.py` now expects the approved B11 Exchange Play refund and still checks persistent one-use negative-effect protection. The isolated Shiko diagnostic passed.
- `tests/test_v5_morozashi_deep.py` now checks the approved B11 rule *requires at least one Grip* (both Grip hands may already be established) rather than the superseded exact-one condition.
- Full suite after Morozashi expectation correction: **45 failed, 363 passed** (GitHub Actions run 40330546900).
- Renamed the matching independent diagnostic workflow test identifier to the current Morozashi test name (commit 30f2bb1); confirm on the next workflow run.
- **Net reduction: 70 to 45 failures**; no production mechanics or approved balance changed during this group of fixes.
