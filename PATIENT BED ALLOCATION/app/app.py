"""
Discharge-Readiness Bed-Turnover Coordination Board
Flask backend — serves all API routes and the main HTML shell.
"""

import json
import os
from datetime import datetime
from flask import Flask, jsonify, render_template, request
from .validator import validate_admission_record, build_validation_summary, freshness_label, parse_ts
from .metrics import compute_turnover_delay, compute_experiment, is_safe_available

app = Flask(__name__)

# ── Load data ─────────────────────────────────────────────────────────────────
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "synthetic_data.json")

def load_data():
    with open(DATA_PATH) as f:
        return json.load(f)

def build_indexes(data):
    """Build lookup indexes for fast access."""
    idx = {}
    idx["admissions"] = {a["admission_id"]: a for a in data["admissions"]}
    idx["milestones_by_adm"] = {}
    for m in data["milestones"]:
        idx["milestones_by_adm"].setdefault(m["admission_id"], []).append(m)
    idx["discharge_orders_by_adm"] = {}
    for d in data["discharge_orders"]:
        idx["discharge_orders_by_adm"].setdefault(d["admission_id"], []).append(d)
    idx["cleaning_by_bed"] = {}
    for c in data["cleaning_events"]:
        idx["cleaning_by_bed"].setdefault(c["bed_id"], []).append(c)
    idx["bed_states_by_bed"] = {}
    for bs in data["bed_states"]:
        idx["bed_states_by_bed"].setdefault(bs["bed_id"], []).append(bs)
    idx["safety_by_adm"] = {}
    for s in data["safety_verifications"]:
        idx["safety_by_adm"].setdefault(s["admission_id"], []).append(s)
    idx["actions_by_adm"] = {}
    for a in data["actions"]:
        idx["actions_by_adm"].setdefault(a["admission_id"], []).append(a)
    return idx


def build_admission_view(adm_id, idx):
    """Assemble full picture for one admission including validation and metrics."""
    adm = idx["admissions"].get(adm_id)
    if not adm:
        return None
    milestones = idx["milestones_by_adm"].get(adm_id, [])
    discharge_orders = idx["discharge_orders_by_adm"].get(adm_id, [])
    discharge_order = discharge_orders[0] if discharge_orders else None
    bed_id = adm.get("bed_id")
    cleaning_list = idx["cleaning_by_bed"].get(bed_id, [])
    # Pick first non-duplicate cleaning
    cleaning = next((c for c in cleaning_list if not c.get("_duplicate")), None)
    bed_states = idx["bed_states_by_bed"].get(bed_id, [])
    safety_list = idx["safety_by_adm"].get(adm_id, [])
    safety = safety_list[0] if safety_list else None
    actions = idx["actions_by_adm"].get(adm_id, [])

    issues = validate_admission_record(adm, milestones, discharge_order,
                                       cleaning, bed_states, safety)

    delay = compute_turnover_delay(adm_id, milestones, cleaning, safety, bed_states, issues)

    # Determine current stage
    stage = _determine_stage(milestones, discharge_order, cleaning, bed_states, safety, issues)

    # Latest bed state
    sorted_bs = sorted(bed_states, key=lambda x: parse_ts(x.get("timestamp")) or datetime.min)
    latest_bed_state = sorted_bs[-1].get("bed_state") if sorted_bs else "UNKNOWN"
    latest_bed_ts = sorted_bs[-1].get("timestamp") if sorted_bs else None

    # Freshness
    freshness_status, freshness_text = freshness_label(latest_bed_ts)

    # Readiness milestone
    ready_ms = [m for m in milestones if m.get("clinical_readiness_status") == "READY"]
    readiness_time = ready_ms[-1].get("milestone_time") if ready_ms else None

    # Elapsed since readiness
    elapsed_min = None
    if readiness_time:
        rt = parse_ts(readiness_time)
        if rt:
            elapsed_min = round((datetime.now().replace(microsecond=0) - rt).total_seconds() / 60)
            # Use prototype NOW
            from .metrics import NOW
            elapsed_min = round((NOW - rt).total_seconds() / 60)

    # Priority escalation
    escalated_actions = [a for a in actions
                         if a.get("escalated") or a.get("status") == "ESCALATED"]

    return {
        "admission_id": adm_id,
        "patient_id": adm.get("patient_id"),
        "facility_id": adm.get("facility_id"),
        "ward": adm.get("ward"),
        "bed_id": bed_id,
        "acuity": adm.get("acuity"),
        "transfer_required": adm.get("transfer_required"),
        "admission_time": adm.get("admission_time"),
        "expected_discharge_date": adm.get("expected_discharge_date"),
        "scenario": adm.get("scenario"),
        "stage": stage,
        "latest_bed_state": latest_bed_state,
        "readiness_time": readiness_time,
        "elapsed_since_readiness_min": elapsed_min,
        "discharge_order": discharge_order,
        "cleaning": cleaning,
        "safety": safety,
        "issues": issues,
        "delay": delay,
        "freshness_status": freshness_status,
        "freshness_text": freshness_text,
        "actions": actions,
        "escalated": len(escalated_actions) > 0,
        "has_issues": len(issues) > 0,
        "issue_codes": list({i["code"] for i in issues}),
    }


STAGE_ORDER = [
    "CLINICAL_READY",
    "DISCHARGE_ORDER",
    "AWAITING_CLEANING",
    "CLEANING",
    "SAFETY_CHECK",
    "SAFE_AVAILABLE",
]


def _determine_stage(milestones, discharge_order, cleaning, bed_states, safety, issues):
    conflict = any(i["code"] == "CONFLICTING" for i in issues)
    safe_bs = [bs for bs in bed_states if bs.get("bed_state") == "SAFE_AVAILABLE"]
    cleaning_bs = [bs for bs in bed_states if bs.get("bed_state") == "CLEANING"]
    await_clean_bs = [bs for bs in bed_states if bs.get("bed_state") == "AWAITING_CLEANING"]
    await_safe_bs = [bs for bs in bed_states if bs.get("bed_state") == "AWAITING_SAFETY_CHECK"]
    unavail_bs = [bs for bs in bed_states if bs.get("bed_state") == "UNAVAILABLE"]

    if unavail_bs:
        return "UNAVAILABLE"
    if safe_bs and not conflict and safety and safety.get("verification_status") == "PASSED":
        return "SAFE_AVAILABLE"
    if await_safe_bs or (cleaning and cleaning.get("completion_time") and not safe_bs):
        return "SAFETY_CHECK"
    if cleaning_bs or (cleaning and cleaning.get("start_time") and not cleaning.get("completion_time")):
        return "CLEANING"
    if await_clean_bs:
        return "AWAITING_CLEANING"
    if discharge_order:
        return "DISCHARGE_ORDER"

    ready_ms = [m for m in milestones if m.get("clinical_readiness_status") == "READY"]
    if ready_ms:
        return "CLINICAL_READY"
    return "ADMITTED"


# ── Build full dataset cache ───────────────────────────────────────────────────

_CACHE = None

def get_cache():
    global _CACHE
    if _CACHE is None:
        _CACHE = refresh_cache()
    return _CACHE

def refresh_cache():
    data = load_data()
    idx = build_indexes(data)
    views = {}
    for adm_id in idx["admissions"]:
        views[adm_id] = build_admission_view(adm_id, idx)

    # Validation summary
    issues_by_adm = {adm_id: v["issues"] for adm_id, v in views.items()}
    validation_summary = build_validation_summary(issues_by_adm)

    # Metrics
    delay_records = [v["delay"] for v in views.values()]
    experiment = compute_experiment(delay_records)

    # Dashboard KPIs
    dashboard = _build_dashboard(views, validation_summary, experiment, data)

    return {
        "views": views,
        "idx": idx,
        "data": data,
        "validation_summary": validation_summary,
        "experiment": experiment,
        "dashboard": dashboard,
    }


def _build_dashboard(views, validation_summary, experiment, data):
    all_beds = set(a["bed_id"] for a in data["admissions"])
    total_beds = len(set(b["bed_id"] for b in data.get("admissions", [])))

    safe_beds = [v for v in views.values() if v["stage"] == "SAFE_AVAILABLE"]
    clinically_ready = [v for v in views.values() if v["stage"] in
                        ("CLINICAL_READY", "DISCHARGE_ORDER", "AWAITING_CLEANING",
                         "CLEANING", "SAFETY_CHECK")]
    pending_discharge_order = [v for v in views.values() if v["stage"] == "CLINICAL_READY"]
    awaiting_cleaning = [v for v in views.values() if v["stage"] == "AWAITING_CLEANING"]
    cleaning_in_progress = [v for v in views.values() if v["stage"] == "CLEANING"]
    awaiting_safety = [v for v in views.values() if v["stage"] == "SAFETY_CHECK"]

    delayed = [v for v in views.values()
               if v["elapsed_since_readiness_min"] is not None
               and v["elapsed_since_readiness_min"] > 120
               and v["stage"] not in ("SAFE_AVAILABLE",)]

    stale = [v for v in views.values() if v["freshness_status"] == "STALE"]
    missing_issues = [v for v in views.values()
                      if any(i["code"] == "MISSING" for i in v["issues"])]
    conflicting_issues = [v for v in views.values()
                          if any(i["code"] == "CONFLICTING" for i in v["issues"])]

    all_actions = []
    for v in views.values():
        all_actions.extend(v["actions"])
    high_priority_unresolved = [a for a in all_actions
                                 if a.get("priority") == "HIGH"
                                 and a.get("status") not in ("RESOLVED",)]

    # Count available beds (safe + not currently re-occupied)
    available_beds = len(safe_beds)

    return {
        "total_beds": len(all_beds),
        "available_beds": available_beds,
        "clinically_ready_discharges": len(clinically_ready),
        "pending_discharge_orders": len(pending_discharge_order),
        "awaiting_cleaning": len(awaiting_cleaning),
        "cleaning_in_progress": len(cleaning_in_progress),
        "awaiting_safety_check": len(awaiting_safety),
        "safe_available_beds": len(safe_beds),
        "delayed_turnovers": len(delayed),
        "stale_data_count": len(stale),
        "missing_data_count": len(missing_issues),
        "conflicting_data_count": len(conflicting_issues),
        "high_priority_unresolved": len(high_priority_unresolved),
        "experiment": experiment,
    }


# ══════════════════════════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/dashboard")
def api_dashboard():
    cache = get_cache()
    return jsonify(cache["dashboard"])


@app.route("/api/admissions")
def api_admissions():
    cache = get_cache()
    # Filters
    facility = request.args.get("facility")
    ward = request.args.get("ward")
    stage = request.args.get("stage")
    priority_filter = request.args.get("priority")
    delayed_only = request.args.get("delayed") == "true"
    stale_only = request.args.get("stale") == "true"
    missing_only = request.args.get("missing") == "true"
    conflicting_only = request.args.get("conflicting") == "true"
    search = request.args.get("search", "").lower()
    role = request.args.get("role", "")

    views = list(cache["views"].values())

    if facility:
        views = [v for v in views if v["facility_id"] == facility]
    if ward:
        views = [v for v in views if v["ward"] == ward]
    if stage:
        views = [v for v in views if v["stage"] == stage]
    if delayed_only:
        views = [v for v in views
                 if v["elapsed_since_readiness_min"] is not None
                 and v["elapsed_since_readiness_min"] > 120
                 and v["stage"] != "SAFE_AVAILABLE"]
    if stale_only:
        views = [v for v in views if v["freshness_status"] == "STALE"]
    if missing_only:
        views = [v for v in views if any(i["code"] == "MISSING" for i in v["issues"])]
    if conflicting_only:
        views = [v for v in views if any(i["code"] == "CONFLICTING" for i in v["issues"])]
    if search:
        views = [v for v in views
                 if search in v["admission_id"].lower()
                 or search in (v["patient_id"] or "").lower()
                 or search in (v["bed_id"] or "").lower()
                 or search in (v["facility_id"] or "").lower()]

    # Role-based filtering
    if role == "housekeeping":
        views = [v for v in views if v["stage"] in ("AWAITING_CLEANING", "CLEANING")]
    elif role == "clinical":
        views = [v for v in views if v["stage"] in ("ADMITTED", "CLINICAL_READY", "DISCHARGE_ORDER")]
    elif role == "nurse":
        views = [v for v in views if v["ward"] is not None]
    elif role == "transfer":
        views = [v for v in views if v.get("transfer_required")]

    # Sort: escalated first, then by elapsed time desc
    views.sort(key=lambda v: (
        not v.get("escalated"),
        -(v["elapsed_since_readiness_min"] or 0)
    ))

    return jsonify(views)


@app.route("/api/admission/<adm_id>")
def api_admission_detail(adm_id):
    cache = get_cache()
    view = cache["views"].get(adm_id)
    if not view:
        return jsonify({"error": "Not found"}), 404

    # Build evidence timeline
    idx = cache["idx"]
    milestones = sorted(
        idx["milestones_by_adm"].get(adm_id, []),
        key=lambda x: parse_ts(x.get("milestone_time")) or datetime.min
    )
    discharge_order = view["discharge_order"]
    cleaning = view["cleaning"]
    safety = view["safety"]
    bed_states = sorted(
        idx["bed_states_by_bed"].get(view["bed_id"], []),
        key=lambda x: parse_ts(x.get("timestamp")) or datetime.min
    )

    timeline = _build_evidence_timeline(
        view, milestones, discharge_order, cleaning, safety, bed_states)

    return jsonify({**view, "timeline": timeline})


def _build_evidence_timeline(view, milestones, discharge_order, cleaning, safety, bed_states):
    events = []
    issues = view["issues"]
    issue_codes = {i["code"] for i in issues}

    def ev(event_type, timestamp, status, source, detail="", quality="VALID"):
        return {
            "event_type": event_type,
            "timestamp": timestamp,
            "status": status,
            "source": source,
            "detail": detail,
            "quality": quality,
        }

    # Admission
    events.append(ev("Admission", view["admission_time"], "ADMITTED",
                     f"Admission record {view['admission_id']}"))

    # Milestones
    for m in milestones:
        q = "VALID"
        if "DUPLICATE" in issue_codes and m.get("_duplicate"):
            q = "DUPLICATE"
        events.append(ev(
            f"Milestone: {m.get('milestone_type','').replace('_',' ').title()}",
            m.get("milestone_time"),
            m.get("clinical_readiness_status", "PENDING"),
            m.get("recorded_by", "Unknown"),
            quality=q
        ))

    # Discharge order
    if discharge_order:
        events.append(ev(
            "Discharge Order",
            discharge_order.get("discharge_order_time"),
            discharge_order.get("discharge_status", "ISSUED"),
            f"Order {discharge_order.get('discharge_order_id')}",
            f"Priority: {discharge_order.get('priority', 'ROUTINE')}"
        ))
    else:
        events.append(ev("Discharge Order", None, "MISSING", "—",
                         "MISSING — Discharge order not found", quality="MISSING"))

    # Bed states
    for bs in bed_states:
        q = "VALID"
        if "INVALID_SEQUENCE" in issue_codes:
            q = "INVALID_SEQUENCE"
        if "CONFLICTING" in issue_codes and bs.get("bed_state") in ("CLEANING", "SAFE_AVAILABLE"):
            q = "CONFLICTING"
        events.append(ev(
            f"Bed State: {bs.get('bed_state','').replace('_',' ')}",
            bs.get("timestamp"),
            bs.get("bed_state"),
            f"Bed {bs.get('bed_id')}",
            f"Safety: {bs.get('safety_check_status','PENDING')}",
            quality=q
        ))

    # Cleaning
    if cleaning:
        q = "VALID"
        if cleaning.get("cleaning_status") in ("STALE",):
            q = "STALE"
        if cleaning.get("cleaning_status") == "INVALID_TIMESTAMP":
            q = "INVALID"
        if "CONFLICTING" in issue_codes:
            q = "CONFLICTING"
        events.append(ev(
            "Cleaning Started",
            cleaning.get("start_time"),
            cleaning.get("cleaning_status"),
            cleaning.get("assigned_to", "Unknown"),
            quality=q
        ))
        events.append(ev(
            "Cleaning Completed",
            cleaning.get("completion_time"),
            cleaning.get("cleaning_status"),
            cleaning.get("assigned_to", "Unknown"),
            f"Status: {cleaning.get('cleaning_status')}",
            quality=q
        ))
    else:
        events.append(ev("Cleaning Completed", None, "MISSING", "—",
                         "MISSING — Cleaning completion not recorded", quality="MISSING"))

    # Safety verification
    if safety and safety.get("verification_status") == "PASSED":
        events.append(ev(
            "Safety Verification",
            safety.get("verification_time"),
            "PASSED",
            safety.get("verified_by", "Unknown"),
            safety.get("notes", "")
        ))
    else:
        q = "MISSING"
        detail = "MISSING — Safety verification not completed"
        if safety:
            detail = f"Safety check: {safety.get('verification_status', 'MISSING')}"
        events.append(ev("Safety Verification", None, "MISSING", "—", detail, quality=q))

    # Safe availability
    safe_bs = [bs for bs in bed_states if bs.get("bed_state") == "SAFE_AVAILABLE"]
    if safe_bs and view["stage"] == "SAFE_AVAILABLE":
        events.append(ev(
            "Safe Bed Available",
            safe_bs[0].get("timestamp"),
            "SAFE_AVAILABLE",
            f"Bed {view['bed_id']}",
            quality="VALID"
        ))
    else:
        events.append(ev("Safe Bed Available", None, "NOT_YET",
                         "—", "Bed not yet safely available", quality="MISSING"))

    # Sort by timestamp, put MISSING at end
    def sort_key(e):
        ts = parse_ts(e.get("timestamp"))
        return ts or datetime(2099, 1, 1)

    events.sort(key=sort_key)
    return events


@app.route("/api/validation")
def api_validation():
    cache = get_cache()
    return jsonify(cache["validation_summary"])


@app.route("/api/experiment")
def api_experiment():
    cache = get_cache()
    return jsonify(cache["experiment"])


@app.route("/api/actions")
def api_actions():
    cache = get_cache()
    all_actions = []
    for v in cache["views"].values():
        for a in v["actions"]:
            all_actions.append({**a,
                                 "facility": v["facility_id"],
                                 "ward": v["ward"],
                                 "bed_id": v["bed_id"]})
    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    all_actions.sort(key=lambda a: (
        0 if a.get("escalated") else 1,
        priority_order.get(a.get("priority", "LOW"), 2)
    ))
    return jsonify(all_actions)


@app.route("/api/actions/<action_id>", methods=["POST"])
def api_update_action(action_id):
    """Update action status: acknowledge / resolve / escalate."""
    cache = get_cache()
    body = request.get_json() or {}
    new_status = body.get("status")
    new_owner = body.get("owner")

    for v in cache["views"].values():
        for a in v["actions"]:
            if a.get("action_id") == action_id:
                if new_status:
                    a["status"] = new_status
                    if new_status == "ACKNOWLEDGED":
                        a["acknowledged_at"] = datetime.now().isoformat()
                    if new_status == "RESOLVED":
                        a["resolved_at"] = datetime.now().isoformat()
                    if new_status == "ESCALATED":
                        a["escalated"] = True
                        a["escalation_level"] = (a.get("escalation_level", 0) + 1)
                if new_owner:
                    a["owner"] = new_owner
                return jsonify({"ok": True, "action": a})
    return jsonify({"error": "Action not found"}), 404


@app.route("/api/error-analysis")
def api_error_analysis():
    cache = get_cache()
    vs = cache["validation_summary"]
    ic = vs["issue_counts"]
    total = vs["total_admissions"]

    def pct(n):
        return round(n / total * 100, 1) if total else 0

    return jsonify({
        "total_records": total,
        "valid_records": vs["valid_admissions"],
        "admissions_with_issues": vs["admissions_with_issues"],
        "pct_affected": vs["pct_affected"],
        "by_type": [
            {
                "type": "MISSING",
                "count": ic["MISSING"],
                "pct": pct(ic["MISSING"]),
                "what_happened": "Required event or field was not recorded",
                "why_matters": "Bed cannot be safely released without complete evidence",
                "how_detected": "Checked for null/absent fields and missing event types",
                "prevention": "Bed blocked from SAFE_AVAILABLE until missing data is resolved",
                "followup": "Action created and assigned to responsible owner",
            },
            {
                "type": "STALE",
                "count": ic["STALE"],
                "pct": pct(ic["STALE"]),
                "what_happened": f"Record has not been updated in >{4}h",
                "why_matters": "Stale data may not reflect true current state",
                "how_detected": "Timestamp compared against prototype reference time",
                "prevention": "Stale records never accepted as fresh — warning displayed",
                "followup": "Action created to re-verify cleaning/safety status",
            },
            {
                "type": "CONFLICTING",
                "count": ic["CONFLICTING"],
                "pct": pct(ic["CONFLICTING"]),
                "what_happened": "Two records disagree on the same event (e.g. bed CLEANING but record says COMPLETED)",
                "why_matters": "Conflicting data means true state is unknown",
                "how_detected": "Cross-checked bed state events against cleaning completion records",
                "prevention": "Safe availability blocked until conflict is resolved",
                "followup": "Conflict resolution action created and assigned",
            },
            {
                "type": "INVALID_SEQUENCE",
                "count": ic["INVALID_SEQUENCE"],
                "pct": pct(ic["INVALID_SEQUENCE"]),
                "what_happened": "Events occurred in impossible order (e.g. safe available before cleaning)",
                "why_matters": "Indicates data entry error or system integrity issue",
                "how_detected": "Validated event timestamps against expected workflow order",
                "prevention": "Invalid sequence flagged — bed not treated as safely available",
                "followup": "Manual review action created",
            },
            {
                "type": "DUPLICATE",
                "count": ic["DUPLICATE"],
                "pct": pct(ic["DUPLICATE"]),
                "what_happened": "Same event recorded more than once",
                "why_matters": "Duplicates can inflate counts or create false confidence",
                "how_detected": "Checked event IDs and timestamps for identical records",
                "prevention": "Duplicate records excluded from metric calculations",
                "followup": "Duplicate flagged in evidence timeline",
            },
            {
                "type": "INVALID",
                "count": ic["INVALID"],
                "pct": pct(ic["INVALID"]),
                "what_happened": "Timestamp or value fails basic validity check (e.g. completion before start)",
                "why_matters": "Invalid data cannot be trusted for decision-making",
                "how_detected": "Timestamp arithmetic and range checks",
                "prevention": "Invalid records not used in metric calculations",
                "followup": "Correction action created",
            },
        ]
    })


@app.route("/api/facilities")
def api_facilities():
    cache = get_cache()
    facilities = sorted(set(v["facility_id"] for v in cache["views"].values() if v["facility_id"]))
    wards = sorted(set(v["ward"] for v in cache["views"].values() if v["ward"]))
    stages = ["ADMITTED", "CLINICAL_READY", "DISCHARGE_ORDER",
              "AWAITING_CLEANING", "CLEANING", "SAFETY_CHECK",
              "SAFE_AVAILABLE", "UNAVAILABLE"]
    return jsonify({"facilities": facilities, "wards": wards, "stages": stages})


if __name__ == "__main__":
    print("Starting Discharge-Readiness Bed-Turnover Coordination Board...")
    print("Open http://127.0.0.1:5000 in your browser")
    app.run(host="0.0.0.0",debug=True, port=5000)
