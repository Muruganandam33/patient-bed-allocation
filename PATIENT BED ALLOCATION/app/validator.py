"""
Data Quality Validation Engine
Detects: MISSING, STALE, CONFLICTING, INVALID, DUPLICATE events
Never silently treats bad data as valid.
"""

from datetime import datetime, timedelta

STALE_THRESHOLD_HOURS = 4   # records older than this relative to "now" are STALE
NOW = datetime(2026, 9, 6, 12, 0, 0)   # prototype reference "now"


def parse_ts(ts_str):
    if not ts_str:
        return None
    try:
        return datetime.fromisoformat(ts_str)
    except Exception:
        return None


def hours_ago(ts):
    if ts is None:
        return None
    delta = NOW - ts
    return round(delta.total_seconds() / 3600, 1)


def freshness_label(ts_str):
    """Return (status, label) for a timestamp."""
    if not ts_str:
        return "MISSING", "MISSING — No timestamp recorded"
    ts = parse_ts(ts_str)
    if ts is None:
        return "INVALID", "INVALID — Timestamp cannot be parsed"
    ago = hours_ago(ts)
    if ago is None:
        return "MISSING", "MISSING — No timestamp"
    if ago < 0:
        return "INVALID", f"INVALID — Timestamp is in the future ({abs(ago):.1f}h ahead)"
    if ago < 1:
        mins = int(ago * 60)
        return "FRESH", f"Updated {mins} minutes ago"
    if ago < 4:
        return "FRESH", f"Updated {ago:.1f} hours ago"
    return "STALE", f"STALE — Last updated {ago:.1f} hours ago"


# ══════════════════════════════════════════════════════════════════════════════
# Per-record validation
# ══════════════════════════════════════════════════════════════════════════════

def validate_admission(adm):
    issues = []
    if not adm.get("patient_id"):
        issues.append({"field": "patient_id", "code": "MISSING", "message": "MISSING — Patient ID not recorded"})
    if not adm.get("bed_id"):
        issues.append({"field": "bed_id", "code": "MISSING", "message": "MISSING — Bed ID not assigned"})
    adm_ts = parse_ts(adm.get("admission_time"))
    exp_ts = parse_ts(adm.get("expected_discharge_date"))
    if adm_ts and exp_ts and exp_ts <= adm_ts:
        issues.append({"field": "expected_discharge_date", "code": "INVALID",
                       "message": "INVALID — Expected discharge is before or at admission time"})
    return issues


def validate_milestones(milestones_for_admission):
    issues = []
    ids_seen = set()
    times = []
    for m in milestones_for_admission:
        mid = m.get("milestone_id")
        if mid in ids_seen:
            issues.append({"field": "milestone_id", "code": "DUPLICATE",
                           "message": f"DUPLICATE — Milestone {mid} appears more than once"})
        ids_seen.add(mid)
        ts = parse_ts(m.get("milestone_time"))
        if ts is None:
            issues.append({"field": "milestone_time", "code": "MISSING",
                           "message": f"MISSING — Milestone {m.get('milestone_type')} has no timestamp"})
        else:
            times.append(ts)
    # Check monotonic order
    for i in range(1, len(times)):
        if times[i] < times[i - 1]:
            issues.append({"field": "milestone_time", "code": "INVALID_SEQUENCE",
                           "message": "INVALID SEQUENCE — Milestones are not in chronological order"})
            break
    return issues


def validate_discharge_order(discharge_order, readiness_time):
    issues = []
    if discharge_order is None:
        return [{"field": "discharge_order", "code": "MISSING",
                 "message": "MISSING — Discharge order not found for this admission"}]
    order_ts = parse_ts(discharge_order.get("discharge_order_time"))
    if order_ts is None:
        issues.append({"field": "discharge_order_time", "code": "MISSING",
                       "message": "MISSING — Discharge order has no timestamp"})
    if order_ts and readiness_time and order_ts < readiness_time:
        issues.append({"field": "discharge_order_time", "code": "INVALID_SEQUENCE",
                       "message": "INVALID SEQUENCE — Discharge order issued before clinical readiness"})
    return issues


def validate_cleaning(cleaning, discharge_order):
    issues = []
    if cleaning is None:
        return [{"field": "cleaning", "code": "MISSING",
                 "message": "MISSING — Cleaning completion not recorded"}]

    start = parse_ts(cleaning.get("start_time"))
    end = parse_ts(cleaning.get("completion_time"))

    if start is None:
        issues.append({"field": "start_time", "code": "MISSING",
                       "message": "MISSING — Cleaning start time not recorded"})
    if end is None:
        issues.append({"field": "completion_time", "code": "MISSING",
                       "message": "MISSING — Cleaning completion time not recorded"})
    if start and end and end < start:
        issues.append({"field": "completion_time", "code": "INVALID",
                       "message": "INVALID — Cleaning completion is before start time"})

    # Stale check on completion
    if end:
        status, label = freshness_label(cleaning.get("completion_time"))
        if status == "STALE":
            issues.append({"field": "completion_time", "code": "STALE",
                           "message": label})

    # Check cleaning started after discharge order
    if discharge_order:
        order_ts = parse_ts(discharge_order.get("discharge_order_time"))
        if start and order_ts and start < order_ts:
            issues.append({"field": "start_time", "code": "INVALID_SEQUENCE",
                           "message": "INVALID SEQUENCE — Cleaning started before discharge order"})
    return issues


def validate_bed_states(bed_states_for_bed):
    issues = []
    ids_seen = set()
    VALID_TRANSITIONS = {
        "OCCUPIED": {"DISCHARGE_PENDING", "AWAITING_CLEANING"},
        "DISCHARGE_PENDING": {"AWAITING_CLEANING", "OCCUPIED"},
        "AWAITING_CLEANING": {"CLEANING", "DISCHARGE_PENDING"},
        "CLEANING": {"AWAITING_SAFETY_CHECK", "AWAITING_CLEANING"},
        "AWAITING_SAFETY_CHECK": {"SAFE_AVAILABLE", "CLEANING"},
        "SAFE_AVAILABLE": {"OCCUPIED", "UNAVAILABLE"},
        "UNAVAILABLE": {"OCCUPIED", "AWAITING_CLEANING"},
    }

    sorted_states = sorted(bed_states_for_bed,
                           key=lambda x: parse_ts(x.get("timestamp")) or datetime.min)
    prev_state = None
    for bs in sorted_states:
        bid = bs.get("bed_state_id")
        if bid in ids_seen:
            issues.append({"field": "bed_state_id", "code": "DUPLICATE",
                           "message": f"DUPLICATE — Bed state event {bid} appears more than once"})
        ids_seen.add(bid)

        curr_state = bs.get("bed_state")
        if prev_state and curr_state:
            allowed = VALID_TRANSITIONS.get(prev_state, set())
            if curr_state not in allowed and curr_state != prev_state:
                issues.append({"field": "bed_state", "code": "INVALID_SEQUENCE",
                               "message": (f"INVALID SEQUENCE — Transition from {prev_state} "
                                           f"to {curr_state} is not permitted")})
        prev_state = curr_state
    return issues


def validate_safety(safety_verification, cleaning):
    issues = []
    if safety_verification is None:
        return [{"field": "safety_verification", "code": "MISSING",
                 "message": "MISSING — Safety verification not found"}]
    if safety_verification.get("verification_status") == "MISSING":
        return [{"field": "safety_verification", "code": "MISSING",
                 "message": "MISSING — Safety verification not completed"}]
    ver_ts = parse_ts(safety_verification.get("verification_time"))
    if ver_ts is None:
        issues.append({"field": "verification_time", "code": "MISSING",
                       "message": "MISSING — Safety verification time not recorded"})
    if cleaning:
        clean_end = parse_ts(cleaning.get("completion_time"))
        if ver_ts and clean_end and ver_ts < clean_end:
            issues.append({"field": "verification_time", "code": "INVALID_SEQUENCE",
                           "message": "INVALID SEQUENCE — Safety verification before cleaning completed"})
    return issues


def detect_conflicts(cleaning, bed_states):
    """Return conflict issues when cleaning and bed states disagree."""
    issues = []
    if cleaning is None:
        return issues
    clean_end = parse_ts(cleaning.get("completion_time"))
    if clean_end is None:
        return issues

    # Latest bed state at time of cleaning completion
    states_before = [
        bs for bs in bed_states
        if parse_ts(bs.get("timestamp")) and parse_ts(bs.get("timestamp")) <= clean_end + timedelta(minutes=30)
    ]
    if not states_before:
        return issues
    latest = sorted(states_before, key=lambda x: parse_ts(x.get("timestamp")))[-1]
    if latest.get("bed_state") == "CLEANING":
        issues.append({"field": "bed_state", "code": "CONFLICTING",
                       "message": ("CONFLICTING — Bed state shows CLEANING IN PROGRESS "
                                   "but cleaning record is marked COMPLETED")})
    return issues


# ══════════════════════════════════════════════════════════════════════════════
# Full admission validation
# ══════════════════════════════════════════════════════════════════════════════

def validate_admission_record(adm, milestones, discharge_order, cleaning,
                               bed_states, safety_verification):
    """Run all checks for one admission. Returns list of issue dicts."""
    all_issues = []

    all_issues += validate_admission(adm)
    all_issues += validate_milestones(milestones)

    readiness_ms = [m for m in milestones if m.get("clinical_readiness_status") == "READY"]
    readiness_time = parse_ts(readiness_ms[-1]["milestone_time"]) if readiness_ms else None

    all_issues += validate_discharge_order(discharge_order, readiness_time)
    all_issues += validate_cleaning(cleaning, discharge_order)
    all_issues += validate_bed_states(bed_states)
    all_issues += validate_safety(safety_verification, cleaning)
    all_issues += detect_conflicts(cleaning, bed_states)

    return all_issues


# ══════════════════════════════════════════════════════════════════════════════
# Dataset-level summary
# ══════════════════════════════════════════════════════════════════════════════

def build_validation_summary(all_issues_by_admission):
    """
    all_issues_by_admission: dict { admission_id: [issue, ...] }
    """
    total = len(all_issues_by_admission)
    valid = 0
    missing = 0
    stale = 0
    conflicting = 0
    invalid_seq = 0
    duplicate = 0
    invalid = 0
    other = 0
    affected_ids = set()

    for adm_id, issues in all_issues_by_admission.items():
        if not issues:
            valid += 1
        else:
            affected_ids.add(adm_id)
            for issue in issues:
                code = issue.get("code", "")
                if code == "MISSING":
                    missing += 1
                elif code == "STALE":
                    stale += 1
                elif code == "CONFLICTING":
                    conflicting += 1
                elif code == "INVALID_SEQUENCE":
                    invalid_seq += 1
                elif code == "DUPLICATE":
                    duplicate += 1
                elif code == "INVALID":
                    invalid += 1
                else:
                    other += 1

    affected = len(affected_ids)
    return {
        "total_admissions": total,
        "valid_admissions": valid,
        "admissions_with_issues": affected,
        "pct_affected": round(affected / total * 100, 1) if total else 0,
        "issue_counts": {
            "MISSING": missing,
            "STALE": stale,
            "CONFLICTING": conflicting,
            "INVALID_SEQUENCE": invalid_seq,
            "DUPLICATE": duplicate,
            "INVALID": invalid,
            "OTHER": other,
        },
        "total_issues": missing + stale + conflicting + invalid_seq + duplicate + invalid + other,
    }
