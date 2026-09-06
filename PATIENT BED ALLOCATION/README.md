# Discharge-Readiness Bed-Turnover Coordination Board

A working end-to-end prototype for coordinating hospital patient transfers between facilities by making discharge readiness and bed turnover status visible to all teams in real time.

---

## Problem

A hospital group transfers patients between facilities. Bed allocation is delayed because clinical discharge readiness is not visible early enough. Different teams — clinical, nursing, housekeeping, and coordinators — work from fragmented, stale, or missing information. No shared view exists showing where a bed is in the turnover pipeline.

## Objective

Reduce the time between **Clinical Discharge Readiness** and **Next Safe Bed Availability** by surfacing real-time, validated bed and discharge status to all teams on a shared coordination board.

## Solution

A web-based coordination board built with Python Flask that:
- Tracks the full workflow from admission through safe bed availability
- Detects and displays missing, stale, conflicting, duplicate, and invalid data
- Calculates the primary metric (turnover coordination delay) from actual data
- Provides role-based views for six staff types
- Creates and escalates follow-up actions automatically
- Never silently treats missing or stale data as valid

## Users

| Role | Focus |
|------|-------|
| Bed Coordinator | Delayed beds, bottlenecks, stale/missing data, urgent actions |
| Doctor / Clinical Team | Clinical readiness, milestones, discharge orders |
| Nurse / Ward Staff | Ward discharge status, pending tasks, next actions |
| Housekeeping | Cleaning queue, progress, overdue tasks |
| Transfer Coordinator | Transfer-ready patients, bed availability, transfer delays |
| Administrator / Management | KPIs, baseline vs target vs result, trends |

## Workflow

```
Admission
  ↓
Clinical Milestones
  ↓
Clinical Discharge Readiness  ← Primary metric start
  ↓
Discharge Order
  ↓
Bed Turnover Required
  ↓
Cleaning
  ↓
Safety Verification
  ↓
Safe Bed Available            ← Primary metric end
  ↓
Bed Allocation / Patient Transfer
```

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.x, Flask |
| Frontend | Vanilla JS, HTML5, CSS3 (no framework dependency) |
| Data | JSON (synthetic dataset, 100 admissions) |
| Tests | Python unittest |
| Charts | Pure CSS bar charts (no external library) |

## Dataset

Synthetic dataset with **100 admissions** across 13 scenario types:

| Scenario | Count | Purpose |
|----------|-------|---------|
| normal | 30 | Clean end-to-end workflow |
| delayed_discharge | 10 | Late clinical readiness |
| delayed_cleaning | 10 | Overdue housekeeping |
| missing_cleaning | 8 | **Edge Case 1** — cleaning not recorded |
| stale_data | 8 | **Edge Case 2** — outdated records |
| conflicting | 6 | **Edge Case 3** — contradictory states |
| duplicate_events | 4 | Duplicate milestone/cleaning records |
| invalid_timestamp | 3 | Completion before start |
| invalid_sequence | 3 | Events in wrong order |
| bed_revert | 4 | Bed reverts to UNAVAILABLE |
| transfer_delay | 4 | Transfer delays |
| missing_safety | 4 | No safety verification |
| escalated_overdue | 3 | Overdue high-priority actions |

## Features

- **Main Dashboard** — 13 KPI cards, primary metric hero, bar charts, admission cards
- **Bed Turnover Board** — Kanban view across 6 workflow stages
- **Role-Based Views** — 6 roles with tailored content
- **Drill-Down Evidence Timeline** — Per-admission event history with quality annotations
- **Freshness Indicators** — FRESH / STALE / MISSING / CONFLICTING labels on every record
- **Action System** — Assign, acknowledge, resolve, escalate follow-up actions
- **Filters & Search** — By facility, ward, stage, priority, delayed, stale, missing, conflicting
- **Accessibility** — Large text, high contrast, icon+text labels, ARIA roles, skip link, keyboard nav

## Primary Metric

**Turnover Coordination Delay** = Next Safe Bed Availability Time − Clinical Discharge Readiness Time

A bed is only counted as safely available when:
1. Cleaning is completed (valid, non-stale record)
2. Safety verification is PASSED
3. Bed state is SAFE_AVAILABLE
4. No active CONFLICTING issues

## Baseline, Target, and Measured Result

| | Value | Source |
|-|-------|--------|
| **Baseline (manual workflow)** | **564.0 min median** | Simulated: actual delay + 165–450 min manual coordination overhead |
| **Target (−20%)** | **451.2 min median** | 20% reduction from baseline |
| **Measured Result** | **242.0 min median** | Calculated from synthetic dataset |
| **Improvement** | **57.1%** | (564 − 242) / 564 × 100 |
| **Target Met** | **Yes** | 57.1% > 20% target |

All values are calculated from the generated synthetic dataset. No values are invented.

## Error Analysis Summary

| Error Type | Count | % of Records | Effect |
|------------|-------|-------------|--------|
| MISSING | 29 | 29% | Blocks safe availability |
| STALE | 8 | 8% | Warning shown, not accepted as fresh |
| CONFLICTING | 6 | 6% | Blocks safe availability |
| INVALID_SEQUENCE | 6 | 6% | Flagged, not used in metrics |
| DUPLICATE | 4 | 4% | Excluded from calculations |
| INVALID | 3 | 3% | Not used in metric calculations |

72 of 100 admissions have at least one data quality issue (72%).

## Edge Cases Tested

1. **Missing Event** — Clinical readiness without cleaning completion: MISSING status, bed blocked, action created
2. **Stale Data** — Cleaning record > 4h old: STALE label with timestamp, not accepted as fresh
3. **Conflicting Events** — Bed says CLEANING, record says COMPLETED: CONFLICTING status, safe availability blocked
4. **Duplicate Events** — Same milestone/cleaning ID twice: flagged, excluded from calculations
5. **Invalid Timestamp** — Cleaning completion before start: INVALID, not used in metrics
6. **Invalid Sequence** — Safe available before cleaning: INVALID_SEQUENCE, blocked
7. **Escalated Overdue** — High-priority overdue action: ESCALATED badge, visible until resolved
8. **Bed Revert** — Bed reverted to UNAVAILABLE after being SAFE_AVAILABLE

## Accessibility

- Font size 16px base, 18–22px headings
- All status shown as text + icon, never colour alone
- ARIA roles on all interactive regions (role="dialog", role="list", aria-live, aria-label)
- Skip navigation link
- All buttons and interactive elements keyboard-accessible
- High-contrast colour scheme
- Freshness shown as text: "STALE — Last updated 6.0 hours ago"
- "Needs Attention" section with explicit next-action text

## Testing

27 test cases covering all core scenarios. All pass.

```
python tests/test_all.py
```

See `docs/test-results.md` for full results.

## Stakeholder Validation

Synthetic stakeholder validation (not real user research) conducted for all 6 roles.
All roles scored YES on identifying delayed beds, understanding readiness, and identifying next actions.
See `docs/evaluation-report.md`.

## Installation

```bash
pip install flask flask-cors pandas numpy
```

No database required. Data is generated as JSON.

## Run Instructions

```bash
# Step 1 — Generate the synthetic dataset (already done, skip if data/synthetic_data.json exists)
python data/generate_data.py

# Step 2 — Start the application
cd app
python app.py

# Step 3 — Open in browser
# http://127.0.0.1:5000
```

## Test Instructions

```bash
python tests/test_all.py
```

## Limitations

- Prototype uses in-memory data (no database persistence). Actions reset on server restart.
- Stale threshold is fixed at 4 hours (not configurable via UI).
- Authentication is a role selector only — no real auth.
- No real-time push updates; page must be navigated to refresh data.
- Synthetic data uses fixed random seed; real deployment needs a live data feed.

## Future Work

- Persistent database (SQLite or PostgreSQL)
- Real-time WebSocket updates
- Actual HL7/FHIR integration for clinical events
- Configurable stale thresholds per facility
- Email/SMS escalation notifications
- Audit log for all state changes
- Multi-language support

---

*Prototype version — September 2026*
