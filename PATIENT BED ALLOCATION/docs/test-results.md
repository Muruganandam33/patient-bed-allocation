# Test Results

## Summary

| | |
|-|-|
| Run date | 6 September 2026 |
| Total tests | 27 |
| Passed | 27 |
| Failed | 0 |
| Errors | 0 |
| Duration | ~0.015 seconds |

**All 27 tests pass.**

## Detailed Results

| TC ID | Test Name | Expected | Actual | Pass/Fail |
|-------|-----------|----------|--------|-----------|
| TC-01 | test_normal_workflow_no_issues | Zero validation issues | Zero issues returned | ✅ Pass |
| TC-01b | test_normal_workflow_safe_available | is_safe_available → True | True | ✅ Pass |
| TC-02 | test_delay_calculated_correctly | status=MEASURED, delay>0 | status=MEASURED, delay=90.0 min | ✅ Pass |
| TC-02b | test_aggregate_stats | mean=120, median=120, min=60, max=180 | mean=120.0, median=120.0, min=60.0, max=180.0 | ✅ Pass |
| TC-02c | test_experiment_calculates_improvement | improvement_pct > 0 | improvement_pct = 57.1 | ✅ Pass |
| TC-03 | test_missing_cleaning_detected | MISSING in issue codes | MISSING detected | ✅ Pass |
| TC-03b | test_missing_cleaning_blocks_safe_availability | False | False, reason="MISSING — Cleaning completion not recorded" | ✅ Pass |
| TC-03c | test_missing_discharge_order_detected | MISSING in issue codes | MISSING detected | ✅ Pass |
| TC-03d | test_missing_safety_blocks_bed | False | False | ✅ Pass |
| TC-04 | test_stale_cleaning_detected | STALE in issue codes | STALE detected | ✅ Pass |
| TC-04b | test_stale_not_treated_as_fresh | False, reason contains STALE | False, "STALE — Cleaning record is outdated" | ✅ Pass |
| TC-04c | test_freshness_label_stale | status=STALE | status=STALE, "STALE — Last updated 6.0 hours ago" | ✅ Pass |
| TC-04d | test_freshness_label_fresh | status=FRESH | status=FRESH | ✅ Pass |
| TC-05 | test_conflict_detected | CONFLICTING in issue codes | CONFLICTING detected | ✅ Pass |
| TC-05b | test_conflict_blocks_safe_availability | False | False, "CONFLICTING events prevent safe availability" | ✅ Pass |
| TC-06 | test_duplicate_milestone_detected | DUPLICATE in issue codes | DUPLICATE detected | ✅ Pass |
| TC-07 | test_cleaning_completion_before_start | INVALID in issue codes | INVALID detected | ✅ Pass |
| TC-07b | test_invalid_timestamp_blocks_safe_availability | False | False | ✅ Pass |
| TC-08 | test_bed_safe_before_cleaning_detected | INVALID_SEQUENCE in issue codes | INVALID_SEQUENCE detected | ✅ Pass |
| TC-08b | test_discharge_order_before_readiness | INVALID_SEQUENCE in issue codes | INVALID_SEQUENCE detected | ✅ Pass |
| TC-09 | test_escalated_action_present | At least 1 escalated action | 3 escalated actions in dataset | ✅ Pass |
| TC-09b | test_high_priority_visible_until_resolved | status != RESOLVED | status = ESCALATED | ✅ Pass |
| TC-10 | test_admissions_count | 100 admissions | 100 admissions | ✅ Pass |
| TC-10b | test_all_admission_ids_unique | All IDs unique | All IDs unique | ✅ Pass |
| TC-10c | test_scenarios_present | 6 edge scenarios present | All 6 present | ✅ Pass |
| TC-10d | test_all_required_keys_present | No missing keys | No missing keys | ✅ Pass |
| TC-10e | test_validation_summary | admissions_with_issues > 0 | 72 admissions with issues | ✅ Pass |

## Failures During Development

Three test cases initially failed due to a test data timing issue: the test helper used timestamps 24–26 hours before the reference NOW, which caused cleaning records to be classified as STALE (> 4h threshold). This was correct system behaviour — the tests needed to use timestamps within the freshness window.

**Root cause:** Test helper `BASE` was set to `datetime(2026, 9, 1, 8, 0, 0)` — 5 days before `NOW`. Cleaning timestamps at BASE+26h were therefore ~120h before NOW, well beyond the 4h stale threshold.

**Fix:** Changed `BASE = NOW - timedelta(hours=3)` and adjusted all test offsets to keep timestamps within the 4-hour freshness window. This confirmed the stale detection logic was working correctly — it had correctly identified old timestamps as stale.

## Raw Test Output

```
test_normal_workflow_no_issues ... ok
test_normal_workflow_safe_available ... ok
test_aggregate_stats ... ok
test_delay_calculated_correctly ... ok
test_experiment_calculates_improvement ... ok
test_missing_cleaning_blocks_safe_availability ... ok
test_missing_cleaning_detected ... ok
test_missing_discharge_order_detected ... ok
test_missing_safety_blocks_bed ... ok
test_freshness_label_fresh ... ok
test_freshness_label_stale ... ok
test_stale_cleaning_detected ... ok
test_stale_not_treated_as_fresh ... ok
test_conflict_blocks_safe_availability ... ok
test_conflict_detected ... ok
test_duplicate_milestone_detected ... ok
test_cleaning_completion_before_start ... ok
test_invalid_timestamp_blocks_safe_availability ... ok
test_bed_safe_before_cleaning_detected ... ok
test_discharge_order_before_readiness ... ok
test_escalated_action_present ... ok
test_high_priority_visible_until_resolved ... ok
test_admissions_count ... ok
test_all_admission_ids_unique ... ok
test_all_required_keys_present ... ok
test_scenarios_present ... ok
test_validation_summary ... ok
----------------------------------------------------------------------
Ran 27 tests in 0.015s
OK
```
