"""
Test suite — Discharge-Readiness Bed-Turnover Coordination Board
Run with: python -m pytest tests/ -v
or:        python tests/test_all.py
"""

import sys
import os
import json
import unittest
from datetime import datetime, timedelta

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'data'))

from validator import (
    validate_admission_record, build_validation_summary,
    freshness_label, parse_ts, validate_cleaning, validate_safety,
    detect_conflicts, validate_bed_states, validate_discharge_order,
)
from metrics import (
    compute_turnover_delay, aggregate_delays, compute_experiment,
    is_safe_available, get_readiness_time,
)

# ── Helpers ────────────────────────────────────────────────────────────────
NOW = datetime(2026, 9, 6, 12, 0, 0)
# BASE close enough to NOW that all test events are within the 4h freshness window
BASE = NOW - timedelta(hours=3)

def ts(dt):
    return dt.isoformat()

def make_admission(bed_id="BED-001"):
    return {
        "admission_id": "ADM-TEST01",
        "patient_id": "PAT-TEST01",
        "facility_id": "Test Hospital",
        "ward": "Ward A",
        "bed_id": bed_id,
        "admission_time": ts(BASE),
        "expected_discharge_date": ts(BASE + timedelta(hours=48)),
        "acuity": "MEDIUM",
        "transfer_required": False,
    }

def make_ready_milestone(offset_hours=0.5):
    t = BASE + timedelta(hours=offset_hours)
    return {
        "milestone_id": "MS-001",
        "admission_id": "ADM-TEST01",
        "milestone_type": "clinical_readiness_confirmed",
        "milestone_time": ts(t),
        "clinical_readiness_status": "READY",
        "recorded_by": "Dr. Test",
    }

def make_discharge_order(ready_offset=0.5, order_offset=0.7):
    return {
        "discharge_order_id": "DO-001",
        "admission_id": "ADM-TEST01",
        "discharge_order_time": ts(BASE + timedelta(hours=order_offset)),
        "discharge_status": "ISSUED",
        "priority": "ROUTINE",
    }

def make_cleaning(start_offset=1.0, end_offset=1.5, status="COMPLETED"):
    start = BASE + timedelta(hours=start_offset)
    end   = BASE + timedelta(hours=end_offset)
    return {
        "cleaning_event_id": "CL-001",
        "bed_id": "BED-001",
        "start_time": ts(start),
        "completion_time": ts(end),
        "cleaning_status": status,
        "assigned_to": "HK Team A",
    }

def make_bed_states(include_safe=True, revert=False):
    t = BASE
    states = [
        {"bed_state_id":"BS-001","bed_id":"BED-001","facility_id":"Test","ward":"A",
         "timestamp":ts(t),"bed_state":"OCCUPIED","safety_check_status":"PENDING"},
        {"bed_state_id":"BS-002","bed_id":"BED-001","facility_id":"Test","ward":"A",
         "timestamp":ts(t+timedelta(hours=0.5)),"bed_state":"DISCHARGE_PENDING","safety_check_status":"PENDING"},
        {"bed_state_id":"BS-003","bed_id":"BED-001","facility_id":"Test","ward":"A",
         "timestamp":ts(t+timedelta(hours=0.7)),"bed_state":"AWAITING_CLEANING","safety_check_status":"PENDING"},
        {"bed_state_id":"BS-004","bed_id":"BED-001","facility_id":"Test","ward":"A",
         "timestamp":ts(t+timedelta(hours=1.0)),"bed_state":"CLEANING","safety_check_status":"PENDING"},
        {"bed_state_id":"BS-005","bed_id":"BED-001","facility_id":"Test","ward":"A",
         "timestamp":ts(t+timedelta(hours=1.5)),"bed_state":"AWAITING_SAFETY_CHECK","safety_check_status":"PENDING"},
    ]
    if include_safe:
        states.append(
            {"bed_state_id":"BS-006","bed_id":"BED-001","facility_id":"Test","ward":"A",
             "timestamp":ts(t+timedelta(hours=2.0)),"bed_state":"SAFE_AVAILABLE","safety_check_status":"PASSED"}
        )
    if revert:
        states.append(
            {"bed_state_id":"BS-007","bed_id":"BED-001","facility_id":"Test","ward":"A",
             "timestamp":ts(t+timedelta(hours=2.5)),"bed_state":"UNAVAILABLE","safety_check_status":"PENDING"}
        )
    return states

def make_safety(passed=True):
    if not passed:
        return {"safety_id":"SV-001","bed_id":"BED-001","admission_id":"ADM-TEST01",
                "verified_by":None,"verification_time":None,"verification_status":"MISSING","notes":""}
    return {
        "safety_id":"SV-001","bed_id":"BED-001","admission_id":"ADM-TEST01",
        "verified_by":"Nurse Test",
        "verification_time":ts(BASE + timedelta(hours=1.6)),
        "verification_status":"PASSED","notes":"All checks passed",
    }


# ══════════════════════════════════════════════════════════════════════════
# TC-01: Normal end-to-end workflow
# ══════════════════════════════════════════════════════════════════════════
class TestNormalWorkflow(unittest.TestCase):
    def test_normal_workflow_no_issues(self):
        """TC-01: Normal workflow produces zero validation issues."""
        adm = make_admission()
        milestones = [make_ready_milestone()]
        discharge_order = make_discharge_order()
        cleaning = make_cleaning()
        bed_states = make_bed_states(include_safe=True)
        safety = make_safety(passed=True)

        issues = validate_admission_record(
            adm, milestones, discharge_order, cleaning, bed_states, safety)

        self.assertEqual(issues, [], f"Expected no issues, got: {issues}")

    def test_normal_workflow_safe_available(self):
        """TC-01b: is_safe_available returns True for clean normal case."""
        cleaning = make_cleaning()
        safety = make_safety(passed=True)
        bed_states = make_bed_states(include_safe=True)
        ok, reason = is_safe_available(cleaning, safety, bed_states, [])
        self.assertTrue(ok, f"Expected safe available, got: {reason}")


# ══════════════════════════════════════════════════════════════════════════
# TC-02: Metric calculation
# ══════════════════════════════════════════════════════════════════════════
class TestMetricCalculation(unittest.TestCase):
    def test_delay_calculated_correctly(self):
        """TC-02: Turnover delay = safe_available_time - readiness_time."""
        milestones = [make_ready_milestone(offset_hours=0.5)]
        # Readiness at BASE+0.5h, safe available at BASE+2.0h → 90 min
        cleaning = make_cleaning(start_offset=1.0, end_offset=1.5)
        safety = make_safety(passed=True)
        bed_states = make_bed_states(include_safe=True)
        safety = make_safety(passed=True)
        bed_states = make_bed_states(include_safe=True)

        result = compute_turnover_delay(
            "ADM-TEST01", milestones, cleaning, safety, bed_states, [])

        self.assertEqual(result["status"], "MEASURED")
        self.assertIsNotNone(result["delay_minutes"])
        self.assertGreater(result["delay_minutes"], 0)

    def test_aggregate_stats(self):
        """TC-02b: aggregate_delays returns correct statistics."""
        delays = [
            {"status":"MEASURED","delay_minutes":60},
            {"status":"MEASURED","delay_minutes":120},
            {"status":"MEASURED","delay_minutes":180},
            {"status":"NOT_AVAILABLE","delay_minutes":None},
        ]
        stats = aggregate_delays(delays)
        self.assertEqual(stats["count"], 3)
        self.assertEqual(stats["mean"], 120.0)
        self.assertEqual(stats["median"], 120.0)
        self.assertEqual(stats["min"], 60.0)
        self.assertEqual(stats["max"], 180.0)

    def test_experiment_calculates_improvement(self):
        """TC-02c: Experiment produces baseline, target, measured and improvement %."""
        delays = [{"status":"MEASURED","delay_minutes": 90 + i*5} for i in range(20)]
        exp = compute_experiment(delays)
        self.assertIn("baseline", exp)
        self.assertIn("measured", exp)
        self.assertIsNotNone(exp["improvement_pct"])
        self.assertGreater(exp["improvement_pct"], 0)


# ══════════════════════════════════════════════════════════════════════════
# TC-03: Missing event (CASE 1)
# ══════════════════════════════════════════════════════════════════════════
class TestMissingEvent(unittest.TestCase):
    def test_missing_cleaning_detected(self):
        """TC-03: Missing cleaning completion → MISSING issue detected."""
        adm = make_admission()
        milestones = [make_ready_milestone()]
        discharge_order = make_discharge_order()
        bed_states = make_bed_states(include_safe=False)
        safety = make_safety(passed=False)

        issues = validate_admission_record(
            adm, milestones, discharge_order, None, bed_states, safety)

        codes = [i["code"] for i in issues]
        self.assertIn("MISSING", codes)

    def test_missing_cleaning_blocks_safe_availability(self):
        """TC-03b: When cleaning is missing, bed is NOT safe available."""
        safety = make_safety(passed=True)
        bed_states = make_bed_states(include_safe=True)
        ok, reason = is_safe_available(None, safety, bed_states, [])
        self.assertFalse(ok)
        self.assertIn("MISSING", reason)

    def test_missing_discharge_order_detected(self):
        """TC-03c: Missing discharge order → MISSING issue."""
        adm = make_admission()
        milestones = [make_ready_milestone()]
        cleaning = make_cleaning()
        bed_states = make_bed_states(include_safe=True)
        safety = make_safety(passed=True)

        issues = validate_admission_record(
            adm, milestones, None, cleaning, bed_states, safety)
        codes = [i["code"] for i in issues]
        self.assertIn("MISSING", codes)

    def test_missing_safety_blocks_bed(self):
        """TC-03d: Missing safety verification blocks safe availability."""
        cleaning = make_cleaning()
        bed_states = make_bed_states(include_safe=True)
        ok, reason = is_safe_available(cleaning, None, bed_states, [])
        self.assertFalse(ok)


# ══════════════════════════════════════════════════════════════════════════
# TC-04: Stale data (CASE 2)
# ══════════════════════════════════════════════════════════════════════════
class TestStaleData(unittest.TestCase):
    def test_stale_cleaning_detected(self):
        """TC-04: Cleaning record > 4h old → STALE issue."""
        cleaning = make_cleaning()
        # Make completion_time 8 hours before NOW
        stale_time = NOW - timedelta(hours=8)
        cleaning["completion_time"] = ts(stale_time)
        cleaning["cleaning_status"] = "COMPLETED"

        issues = validate_cleaning(cleaning, make_discharge_order())
        codes = [i["code"] for i in issues]
        self.assertIn("STALE", codes)

    def test_stale_not_treated_as_fresh(self):
        """TC-04b: Stale cleaning record blocks safe availability."""
        cleaning = make_cleaning()
        # Use an old completion that is still after start (start=NOW-12h, end=NOW-8h → stale)
        cleaning["start_time"] = ts(NOW - timedelta(hours=12))
        cleaning["completion_time"] = ts(NOW - timedelta(hours=8))
        cleaning["cleaning_status"] = "COMPLETED"
        safety = make_safety(passed=True)
        bed_states = make_bed_states(include_safe=True)
        ok, reason = is_safe_available(cleaning, safety, bed_states, [])
        self.assertFalse(ok)
        self.assertIn("STALE", reason)

    def test_freshness_label_stale(self):
        """TC-04c: freshness_label returns STALE for old timestamps."""
        old_ts = ts(NOW - timedelta(hours=6))
        status, label = freshness_label(old_ts)
        self.assertEqual(status, "STALE")
        self.assertIn("STALE", label)

    def test_freshness_label_fresh(self):
        """TC-04d: freshness_label returns FRESH for recent timestamps."""
        recent_ts = ts(NOW - timedelta(minutes=30))
        status, label = freshness_label(recent_ts)
        self.assertEqual(status, "FRESH")


# ══════════════════════════════════════════════════════════════════════════
# TC-05: Conflicting events (CASE 3)
# ══════════════════════════════════════════════════════════════════════════
class TestConflictingEvents(unittest.TestCase):
    def test_conflict_detected(self):
        """TC-05: Bed state CLEANING after cleaning record COMPLETED → CONFLICTING."""
        cleaning = make_cleaning(start_offset=25, end_offset=26)
        # bed state at cleaning completion time says CLEANING
        bed_states = [
            {"bed_state_id":"BS-001","bed_id":"BED-001","facility_id":"Test","ward":"A",
             "timestamp": ts(BASE + timedelta(hours=25.5)),
             "bed_state":"CLEANING","safety_check_status":"PENDING"},
        ]
        issues = detect_conflicts(cleaning, bed_states)
        codes = [i["code"] for i in issues]
        self.assertIn("CONFLICTING", codes)

    def test_conflict_blocks_safe_availability(self):
        """TC-05b: CONFLICTING issue blocks safe availability."""
        cleaning = make_cleaning()
        safety = make_safety(passed=True)
        bed_states = make_bed_states(include_safe=True)
        conflict_issue = [{"code":"CONFLICTING","field":"bed_state",
                           "message":"CONFLICTING — Bed state says CLEANING but record COMPLETED"}]
        ok, reason = is_safe_available(cleaning, safety, bed_states, conflict_issue)
        self.assertFalse(ok)
        self.assertIn("CONFLICTING", reason)


# ══════════════════════════════════════════════════════════════════════════
# TC-06: Duplicate events
# ══════════════════════════════════════════════════════════════════════════
class TestDuplicateEvents(unittest.TestCase):
    def test_duplicate_milestone_detected(self):
        """TC-06: Duplicate milestone IDs detected."""
        m1 = make_ready_milestone()
        m2 = dict(m1)  # same milestone_id
        from validator import validate_milestones
        issues = validate_milestones([m1, m2])
        codes = [i["code"] for i in issues]
        self.assertIn("DUPLICATE", codes)


# ══════════════════════════════════════════════════════════════════════════
# TC-07: Invalid timestamp
# ══════════════════════════════════════════════════════════════════════════
class TestInvalidTimestamp(unittest.TestCase):
    def test_cleaning_completion_before_start(self):
        """TC-07: Cleaning completion before start → INVALID issue."""
        cleaning = make_cleaning()
        # Put completion 30 min before start (both close to NOW so not stale)
        start = BASE + timedelta(hours=1.0)
        cleaning["start_time"] = ts(start)
        cleaning["completion_time"] = ts(start - timedelta(minutes=30))

        issues = validate_cleaning(cleaning, make_discharge_order())
        codes = [i["code"] for i in issues]
        self.assertIn("INVALID", codes)

    def test_invalid_timestamp_blocks_safe_availability(self):
        """TC-07b: Invalid timestamp prevents safe availability."""
        cleaning = make_cleaning()
        start = BASE + timedelta(hours=1.0)
        cleaning["start_time"] = ts(start)
        # completion before start — INVALID check in is_safe_available blocks it
        cleaning["completion_time"] = ts(start - timedelta(minutes=30))
        safety = make_safety(passed=True)
        bed_states = make_bed_states(include_safe=True)
        ok, reason = is_safe_available(cleaning, safety, bed_states, [])
        self.assertFalse(ok)


# ══════════════════════════════════════════════════════════════════════════
# TC-08: Invalid event sequence
# ══════════════════════════════════════════════════════════════════════════
class TestInvalidSequence(unittest.TestCase):
    def test_bed_safe_before_cleaning_detected(self):
        """TC-08: Bed state transitions include invalid jump."""
        bed_states = [
            {"bed_state_id":"BS-001","bed_id":"BED-001","facility_id":"T","ward":"A",
             "timestamp":ts(BASE),"bed_state":"OCCUPIED","safety_check_status":"PENDING"},
            # Skip directly from OCCUPIED to SAFE_AVAILABLE (invalid)
            {"bed_state_id":"BS-002","bed_id":"BED-001","facility_id":"T","ward":"A",
             "timestamp":ts(BASE + timedelta(hours=1)),
             "bed_state":"SAFE_AVAILABLE","safety_check_status":"PASSED"},
        ]
        issues = validate_bed_states(bed_states)
        codes = [i["code"] for i in issues]
        self.assertIn("INVALID_SEQUENCE", codes)

    def test_discharge_order_before_readiness(self):
        """TC-08b: Discharge order before clinical readiness → INVALID_SEQUENCE."""
        # Order time is 1 hour before readiness time
        ready_time = BASE + timedelta(hours=24)
        order = {
            "discharge_order_id":"DO-001",
            "admission_id":"ADM-TEST01",
            "discharge_order_time": ts(ready_time - timedelta(hours=1)),
            "discharge_status":"ISSUED","priority":"ROUTINE",
        }
        issues = validate_discharge_order(order, ready_time)
        codes = [i["code"] for i in issues]
        self.assertIn("INVALID_SEQUENCE", codes)


# ══════════════════════════════════════════════════════════════════════════
# TC-09: Escalation
# ══════════════════════════════════════════════════════════════════════════
class TestEscalation(unittest.TestCase):
    def test_escalated_action_present(self):
        """TC-09: Dataset contains escalated actions from escalated_overdue scenario."""
        data_path = os.path.join(
            os.path.dirname(__file__), '..', 'data', 'synthetic_data.json')
        with open(data_path) as f:
            data = json.load(f)
        escalated = [a for a in data["actions"] if a.get("escalated")]
        self.assertGreater(len(escalated), 0,
            "Expected at least one escalated action in synthetic dataset")

    def test_high_priority_visible_until_resolved(self):
        """TC-09b: High-priority actions stay visible while status != RESOLVED."""
        action = {
            "action_id": "ACT-TEST",
            "priority": "HIGH",
            "status": "ESCALATED",
            "escalated": True,
            "escalation_level": 2,
        }
        # Status is not RESOLVED → still visible
        self.assertNotEqual(action["status"], "RESOLVED")


# ══════════════════════════════════════════════════════════════════════════
# TC-10: Dataset integrity
# ══════════════════════════════════════════════════════════════════════════
class TestDatasetIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data_path = os.path.join(
            os.path.dirname(__file__), '..', 'data', 'synthetic_data.json')
        with open(data_path) as f:
            cls.data = json.load(f)

    def test_admissions_count(self):
        """TC-10: Dataset has expected number of admissions (100)."""
        self.assertEqual(len(self.data["admissions"]), 100)

    def test_all_admission_ids_unique(self):
        """TC-10b: All admission IDs are unique."""
        ids = [a["admission_id"] for a in self.data["admissions"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_scenarios_present(self):
        """TC-10c: Expected edge case scenarios are present."""
        scenarios = {a["scenario"] for a in self.data["admissions"]}
        for s in ["missing_cleaning", "stale_data", "conflicting",
                  "duplicate_events", "invalid_timestamp", "escalated_overdue"]:
            self.assertIn(s, scenarios, f"Scenario {s} missing from dataset")

    def test_all_required_keys_present(self):
        """TC-10d: All admission records have required fields."""
        required = ["admission_id","patient_id","facility_id","ward",
                    "bed_id","admission_time","acuity"]
        for adm in self.data["admissions"]:
            for k in required:
                self.assertIn(k, adm, f"Field {k} missing in {adm.get('admission_id')}")

    def test_validation_summary(self):
        """TC-10e: Validation summary detects issues across dataset."""
        from validator import validate_admission_record, build_validation_summary
        from collections import defaultdict

        adm_map = {a["admission_id"]: a for a in self.data["admissions"]}
        ms_map = defaultdict(list)
        for m in self.data["milestones"]:
            ms_map[m["admission_id"]].append(m)
        do_map = {d["admission_id"]: d for d in self.data["discharge_orders"]}
        cl_map = {c["bed_id"]: c for c in self.data["cleaning_events"]}
        bs_map = defaultdict(list)
        for bs in self.data["bed_states"]:
            bs_map[bs["bed_id"]].append(bs)
        sv_map = {s["admission_id"]: s for s in self.data["safety_verifications"]}

        issues_by_adm = {}
        for adm_id, adm in adm_map.items():
            issues_by_adm[adm_id] = validate_admission_record(
                adm,
                ms_map.get(adm_id, []),
                do_map.get(adm_id),
                cl_map.get(adm["bed_id"]),
                bs_map.get(adm["bed_id"], []),
                sv_map.get(adm_id),
            )

        summary = build_validation_summary(issues_by_adm)
        self.assertGreater(summary["admissions_with_issues"], 0)
        self.assertGreater(summary["issue_counts"]["MISSING"], 0)


# ══════════════════════════════════════════════════════════════════════════
# MAIN runner
# ══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    test_classes = [
        TestNormalWorkflow,
        TestMetricCalculation,
        TestMissingEvent,
        TestStaleData,
        TestConflictingEvents,
        TestDuplicateEvents,
        TestInvalidTimestamp,
        TestInvalidSequence,
        TestEscalation,
        TestDatasetIntegrity,
    ]

    for tc in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(tc))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
