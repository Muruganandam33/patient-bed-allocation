"""
Synthetic Dataset Generator
Hospital Discharge-Readiness Bed-Turnover Coordination Board

Generates realistic synthetic data including:
- Normal workflows
- Delayed discharge / delayed cleaning
- Missing events
- Stale events
- Conflicting events
- Duplicate events
- Invalid event sequences
- Bed becoming unavailable again
- Transfer delays
"""

import json
import random
import uuid
from datetime import datetime, timedelta

random.seed(42)

BASE_TIME = datetime(2026, 9, 1, 6, 0, 0)

FACILITIES = ["City General Hospital", "North District Medical", "Eastside Clinic"]
WARDS = {
    "City General Hospital": ["Ward A", "Ward B", "Ward C", "ICU"],
    "North District Medical": ["Ward D", "Ward E", "Surgical"],
    "Eastside Clinic": ["Ward F", "Recovery"],
}
ACUITY_LEVELS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
STAFF = [
    "Dr. Smith", "Dr. Patel", "Dr. Nguyen", "Dr. Garcia",
    "Nurse Johnson", "Nurse Williams", "Nurse Brown", "Nurse Lee",
    "HK Team A", "HK Team B", "HK Team C",
    "Coordinator Adams", "Coordinator Evans",
]

MILESTONE_TYPES = [
    "labs_reviewed", "imaging_reviewed", "specialist_cleared",
    "medication_reconciled", "discharge_summary_written",
    "family_notified", "transport_arranged"
]

CLEANING_STAFF = ["HK Team A", "HK Team B", "HK Team C", "HK Solo Porter"]

# ── scenario tags ──────────────────────────────────────────────────────────────
# Each admission gets exactly one scenario tag that drives how its events look.
SCENARIOS = {
    "normal": 30,            # 30 admissions: clean end-to-end
    "delayed_discharge": 10,
    "delayed_cleaning": 10,
    "missing_cleaning": 8,   # CASE 1
    "stale_data": 8,         # CASE 2
    "conflicting": 6,        # CASE 3
    "duplicate_events": 4,
    "invalid_timestamp": 3,
    "invalid_sequence": 3,
    "bed_revert": 4,
    "transfer_delay": 4,
    "missing_safety": 4,
    "missing_discharge_order": 3,
    "escalated_overdue": 3,
}


def fmt(dt):
    return dt.isoformat()


def rnd_minutes(lo, hi):
    return timedelta(minutes=random.randint(lo, hi))


def new_id(prefix=""):
    return prefix + str(uuid.uuid4())[:8].upper()


# ── bed pool ───────────────────────────────────────────────────────────────────
def build_bed_pool():
    beds = []
    bid = 1
    for facility in FACILITIES:
        for ward in WARDS[facility]:
            n = random.randint(6, 12)
            for _ in range(n):
                beds.append({
                    "bed_id": f"BED-{bid:03d}",
                    "facility_id": facility,
                    "ward": ward,
                })
                bid += 1
    return beds


BED_POOL = build_bed_pool()
_bed_idx = 0


def next_bed():
    global _bed_idx
    b = BED_POOL[_bed_idx % len(BED_POOL)]
    _bed_idx += 1
    return b


# ══════════════════════════════════════════════════════════════════════════════
# ADMISSION
# ══════════════════════════════════════════════════════════════════════════════

def make_admission(scenario, offset_hours):
    bed = next_bed()
    adm_time = BASE_TIME + timedelta(hours=offset_hours, minutes=random.randint(0, 59))
    stay_hours = random.randint(24, 120)
    expected_discharge = adm_time + timedelta(hours=stay_hours)
    return {
        "admission_id": new_id("ADM-"),
        "patient_id": new_id("PAT-"),
        "facility_id": bed["facility_id"],
        "ward": bed["ward"],
        "bed_id": bed["bed_id"],
        "admission_time": fmt(adm_time),
        "expected_discharge_date": fmt(expected_discharge),
        "acuity": random.choice(ACUITY_LEVELS),
        "transfer_required": random.choice([True, False]),
        "scenario": scenario,
        "_adm_time": adm_time,
        "_stay_hours": stay_hours,
    }


# ══════════════════════════════════════════════════════════════════════════════
# CLINICAL MILESTONES
# ══════════════════════════════════════════════════════════════════════════════

def make_milestones(adm, scenario):
    adm_time = adm["_adm_time"]
    stay = adm["_stay_hours"]
    milestones = []
    # Pick 3-6 milestone types
    chosen = random.sample(MILESTONE_TYPES, k=random.randint(3, 6))
    t = adm_time + timedelta(hours=stay * 0.6)
    for mt in chosen:
        t += rnd_minutes(20, 90)
        milestones.append({
            "milestone_id": new_id("MS-"),
            "admission_id": adm["admission_id"],
            "milestone_type": mt,
            "milestone_time": fmt(t),
            "clinical_readiness_status": "PENDING",
            "recorded_by": random.choice(STAFF[:8]),
        })

    # Final readiness milestone
    readiness_time = t + rnd_minutes(10, 30)

    if scenario == "delayed_discharge":
        readiness_time += timedelta(hours=random.randint(3, 8))

    milestones.append({
        "milestone_id": new_id("MS-"),
        "admission_id": adm["admission_id"],
        "milestone_type": "clinical_readiness_confirmed",
        "milestone_time": fmt(readiness_time),
        "clinical_readiness_status": "READY",
        "recorded_by": random.choice(STAFF[:4]),
        "_is_readiness": True,
    })
    return milestones, readiness_time


# ══════════════════════════════════════════════════════════════════════════════
# DISCHARGE ORDER
# ══════════════════════════════════════════════════════════════════════════════

def make_discharge_order(adm, readiness_time, scenario):
    if scenario == "missing_discharge_order":
        return None  # intentionally missing
    order_delay = rnd_minutes(5, 30)
    if scenario == "delayed_discharge":
        order_delay += timedelta(hours=random.randint(1, 4))
    order_time = readiness_time + order_delay
    return {
        "discharge_order_id": new_id("DO-"),
        "admission_id": adm["admission_id"],
        "discharge_order_time": fmt(order_time),
        "discharge_status": "ISSUED",
        "priority": random.choice(["ROUTINE", "URGENT", "STAT"]),
        "_order_time": order_time,
    }


# ══════════════════════════════════════════════════════════════════════════════
# CLEANING EVENT
# ══════════════════════════════════════════════════════════════════════════════

def make_cleaning(adm, order_time, scenario):
    if scenario == "missing_cleaning":
        return None  # CASE 1 – intentionally missing

    start_delay = rnd_minutes(10, 40)
    if scenario == "delayed_cleaning":
        start_delay += timedelta(hours=random.randint(2, 5))

    start_time = order_time + start_delay
    duration = rnd_minutes(20, 60)
    completion_time = start_time + duration

    cleaning_status = "COMPLETED"

    event = {
        "cleaning_event_id": new_id("CL-"),
        "bed_id": adm["bed_id"],
        "start_time": fmt(start_time),
        "completion_time": fmt(completion_time),
        "cleaning_status": cleaning_status,
        "assigned_to": random.choice(CLEANING_STAFF),
        "_start_time": start_time,
        "_completion_time": completion_time,
    }

    # CASE 2 – stale: completion timestamp is very old (> 4 hours before "now")
    if scenario == "stale_data":
        stale_time = start_time - timedelta(hours=random.randint(5, 12))
        event["completion_time"] = fmt(stale_time)
        event["_completion_time"] = stale_time
        event["cleaning_status"] = "STALE"

    # CASE 3 – conflicting: cleaning shows COMPLETED but bed state will say IN_PROGRESS
    if scenario == "conflicting":
        event["cleaning_status"] = "COMPLETED"

    # invalid timestamp: completion before start
    if scenario == "invalid_timestamp":
        bad_time = start_time - timedelta(hours=1)
        event["completion_time"] = fmt(bad_time)
        event["_completion_time"] = bad_time
        event["cleaning_status"] = "INVALID_TIMESTAMP"

    return event


# ══════════════════════════════════════════════════════════════════════════════
# BED STATE EVENTS
# ══════════════════════════════════════════════════════════════════════════════

VALID_BED_STATES = [
    "OCCUPIED", "DISCHARGE_PENDING", "AWAITING_CLEANING",
    "CLEANING", "AWAITING_SAFETY_CHECK", "SAFE_AVAILABLE", "UNAVAILABLE"
]


def make_bed_states(adm, cleaning, readiness_time, scenario):
    events = []
    t = adm["_adm_time"]

    def bs(state, ts, safety="PENDING"):
        return {
            "bed_state_id": new_id("BS-"),
            "bed_id": adm["bed_id"],
            "facility_id": adm["facility_id"],
            "ward": adm["ward"],
            "timestamp": fmt(ts),
            "bed_state": state,
            "safety_check_status": safety,
            "_ts": ts,
        }

    events.append(bs("OCCUPIED", t))
    events.append(bs("DISCHARGE_PENDING", readiness_time + rnd_minutes(1, 5)))

    if scenario == "missing_cleaning":
        # skip cleaning states — bed stays stuck
        events.append(bs("AWAITING_CLEANING", readiness_time + rnd_minutes(10, 20)))
        return events

    if cleaning is None:
        events.append(bs("AWAITING_CLEANING", readiness_time + rnd_minutes(10, 20)))
        return events

    clean_start = cleaning["_start_time"]
    clean_end = cleaning["_completion_time"]

    events.append(bs("AWAITING_CLEANING", clean_start - rnd_minutes(2, 8)))
    events.append(bs("CLEANING", clean_start + rnd_minutes(1, 3)))

    if scenario == "conflicting":
        # CASE 3: bed says CLEANING but cleaning record says COMPLETED
        events.append(bs("CLEANING", clean_end + rnd_minutes(5, 15)))
        return events

    if scenario == "bed_revert":
        # Bed becomes SAFE_AVAILABLE, then reverts to UNAVAILABLE
        safety_time = clean_end + rnd_minutes(10, 25)
        events.append(bs("AWAITING_SAFETY_CHECK", clean_end + rnd_minutes(3, 8)))
        events.append(bs("SAFE_AVAILABLE", safety_time, "PASSED"))
        events.append(bs("UNAVAILABLE", safety_time + rnd_minutes(15, 60)))
        return events

    if scenario == "invalid_sequence":
        # SAFE_AVAILABLE before cleaning completed
        events.append(bs("SAFE_AVAILABLE", clean_start - rnd_minutes(5, 10), "PASSED"))
        return events

    if scenario == "missing_safety":
        # Skip AWAITING_SAFETY_CHECK — never gets safety check
        events.append(bs("AWAITING_SAFETY_CHECK", clean_end + rnd_minutes(3, 8)))
        return events

    safety_time = clean_end + rnd_minutes(10, 25)
    events.append(bs("AWAITING_SAFETY_CHECK", clean_end + rnd_minutes(3, 8)))
    events.append(bs("SAFE_AVAILABLE", safety_time, "PASSED"))

    return events


# ══════════════════════════════════════════════════════════════════════════════
# SAFETY VERIFICATION
# ══════════════════════════════════════════════════════════════════════════════

def make_safety_verification(adm, bed_states, scenario):
    safe_events = [e for e in bed_states if e["bed_state"] == "SAFE_AVAILABLE"]
    if not safe_events or scenario in ("missing_safety", "missing_cleaning",
                                       "conflicting", "invalid_sequence",
                                       "missing_discharge_order"):
        return {
            "safety_id": new_id("SV-"),
            "bed_id": adm["bed_id"],
            "admission_id": adm["admission_id"],
            "verified_by": None,
            "verification_time": None,
            "verification_status": "MISSING",
            "notes": "Safety verification not completed",
        }
    safe_ts = safe_events[0]["_ts"]
    return {
        "safety_id": new_id("SV-"),
        "bed_id": adm["bed_id"],
        "admission_id": adm["admission_id"],
        "verified_by": random.choice(STAFF[4:8]),
        "verification_time": fmt(safe_ts + rnd_minutes(1, 5)),
        "verification_status": "PASSED",
        "notes": "All checks passed",
    }


# ══════════════════════════════════════════════════════════════════════════════
# DUPLICATE EVENTS
# ══════════════════════════════════════════════════════════════════════════════

def inject_duplicates(milestones, cleaning_events):
    """Add duplicate milestone and cleaning records for duplicate-event scenario."""
    dupes_m = []
    dupes_c = []
    for m in milestones:
        if m.get("_is_readiness") and random.random() < 0.5:
            dup = dict(m)
            dup["milestone_id"] = new_id("MS-DUP-")
            dup["_duplicate"] = True
            dupes_m.append(dup)
    for c in cleaning_events:
        if c and random.random() < 0.4:
            dup = dict(c)
            dup["cleaning_event_id"] = new_id("CL-DUP-")
            dup["_duplicate"] = True
            dupes_c.append(dup)
    return dupes_m, dupes_c


# ══════════════════════════════════════════════════════════════════════════════
# ACTIONS (follow-up / escalation)
# ══════════════════════════════════════════════════════════════════════════════

def make_action(admission_id, issue, owner, priority, due_offset_hours,
                status="OPEN", escalated=False):
    due = BASE_TIME + timedelta(hours=random.randint(1, 48))
    return {
        "action_id": new_id("ACT-"),
        "admission_id": admission_id,
        "issue": issue,
        "owner": owner,
        "priority": priority,
        "due_datetime": fmt(due + timedelta(hours=due_offset_hours)),
        "status": status,
        "escalation_level": 2 if escalated else 0,
        "escalated": escalated,
        "created_at": fmt(BASE_TIME),
        "acknowledged_at": None,
        "resolved_at": None,
    }


# ══════════════════════════════════════════════════════════════════════════════
# MAIN GENERATION
# ══════════════════════════════════════════════════════════════════════════════

def generate():
    admissions = []
    all_milestones = []
    all_discharge_orders = []
    all_cleaning_events = []
    all_bed_states = []
    all_safety_verifications = []
    all_actions = []

    offset = 0
    for scenario, count in SCENARIOS.items():
        for _ in range(count):
            adm = make_admission(scenario, offset)
            offset += random.randint(1, 4)

            milestones, readiness_time = make_milestones(adm, scenario)
            discharge_order = make_discharge_order(adm, readiness_time, scenario)
            order_time = (discharge_order["_order_time"]
                          if discharge_order else readiness_time + timedelta(hours=1))
            cleaning = make_cleaning(adm, order_time, scenario)
            bed_states = make_bed_states(adm, cleaning, readiness_time, scenario)
            safety = make_safety_verification(adm, bed_states, scenario)

            # Inject duplicates for duplicate scenario
            if scenario == "duplicate_events":
                dup_m, dup_c = inject_duplicates(milestones, [cleaning] if cleaning else [])
                milestones += dup_m
                if dup_c:
                    all_cleaning_events += dup_c

            # Strip internal _keys before saving
            def clean(obj):
                if obj is None:
                    return None
                return {k: v for k, v in obj.items() if not k.startswith("_")}

            admissions.append(clean(adm))
            all_milestones += [clean(m) for m in milestones]
            if discharge_order:
                all_discharge_orders.append(clean(discharge_order))
            if cleaning:
                all_cleaning_events.append(clean(cleaning))
            all_bed_states += [clean(bs) for bs in bed_states]
            all_safety_verifications.append(safety)

            # Auto-create actions for problem scenarios
            adm_id = adm["admission_id"]
            if scenario == "missing_cleaning":
                all_actions.append(make_action(
                    adm_id, "Cleaning completion not recorded — bed cannot be released",
                    "HK Team A", "HIGH", 2))
            if scenario == "stale_data":
                all_actions.append(make_action(
                    adm_id, "STALE: Cleaning record is outdated — please re-verify",
                    "HK Team B", "HIGH", 1))
            if scenario == "conflicting":
                all_actions.append(make_action(
                    adm_id, "CONFLICTING: Bed state says CLEANING but record says COMPLETED",
                    "Coordinator Adams", "HIGH", 0))
            if scenario == "missing_safety":
                all_actions.append(make_action(
                    adm_id, "Safety verification missing — bed cannot be marked SAFE",
                    "Nurse Johnson", "HIGH", 1))
            if scenario == "escalated_overdue":
                all_actions.append(make_action(
                    adm_id,
                    "HIGH-PRIORITY overdue: Transfer delayed > 4 hours",
                    "Coordinator Evans", "HIGH", -2,
                    status="ESCALATED", escalated=True))
            if scenario == "missing_discharge_order":
                all_actions.append(make_action(
                    adm_id, "Discharge order not found — clinical team action required",
                    "Dr. Smith", "MEDIUM", 3))
            if scenario == "delayed_cleaning":
                all_actions.append(make_action(
                    adm_id, "Cleaning overdue — bed has been awaiting cleaning > 2 hours",
                    "HK Team C", "MEDIUM", 1))
            if scenario == "transfer_delay":
                all_actions.append(make_action(
                    adm_id, "Transfer delayed — patient ready but no receiving bed confirmed",
                    "Coordinator Adams", "HIGH", 1))

    return {
        "admissions": admissions,
        "milestones": all_milestones,
        "discharge_orders": all_discharge_orders,
        "cleaning_events": all_cleaning_events,
        "bed_states": all_bed_states,
        "safety_verifications": all_safety_verifications,
        "actions": all_actions,
        "metadata": {
            "generated_at": fmt(datetime.now()),
            "base_time": fmt(BASE_TIME),
            "total_admissions": len(admissions),
            "total_milestones": len(all_milestones),
            "total_discharge_orders": len(all_discharge_orders),
            "total_cleaning_events": len(all_cleaning_events),
            "total_bed_states": len(all_bed_states),
            "total_safety_verifications": len(all_safety_verifications),
            "total_actions": len(all_actions),
            "scenarios": list(SCENARIOS.keys()),
        }
    }


if __name__ == "__main__":
    import os
    data = generate()
    out_path = os.path.join(os.path.dirname(__file__), "synthetic_data.json")
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2)
    m = data["metadata"]
    print(f"Generated synthetic dataset:")
    print(f"  Admissions:           {m['total_admissions']}")
    print(f"  Milestones:           {m['total_milestones']}")
    print(f"  Discharge orders:     {m['total_discharge_orders']}")
    print(f"  Cleaning events:      {m['total_cleaning_events']}")
    print(f"  Bed state events:     {m['total_bed_states']}")
    print(f"  Safety verifications: {m['total_safety_verifications']}")
    print(f"  Actions:              {m['total_actions']}")
    print(f"Saved to: {out_path}")
