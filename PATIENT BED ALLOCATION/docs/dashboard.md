# Dashboard Documentation

## Main Dashboard (`/`)

The main dashboard is the landing page for all roles. It adapts its focus based on the selected role.

### Role Banner

Displays the current role, icon, and a plain-language description of what is shown. Updates immediately when the role selector is changed.

### Needs Immediate Attention

A red-bordered banner that appears when any admission has:
- An ESCALATED action, or
- A CONFLICTING data issue, or
- A MISSING data issue

Shows up to 5 items with bed ID, ward, facility, issue chips, and a direct "View Detail →" link. This section is prominently placed above all other content so that urgent items cannot be missed.

### KPI Cards (13 cards)

| Card | Colour | Description |
|------|--------|-------------|
| Total Beds | Blue | All beds in the dataset |
| Available Beds | Green | Beds currently in SAFE_AVAILABLE state |
| Clinically Ready Discharges | Blue | Admissions that have reached clinical readiness and are in the turnover pipeline |
| Pending Discharge Orders | Grey | Admissions with clinical readiness but no discharge order yet |
| Awaiting Cleaning | Orange | Beds waiting for housekeeping |
| Cleaning in Progress | Orange | Beds currently being cleaned |
| Awaiting Safety Check | Orange | Beds cleaned but not yet safety-verified |
| Safe Available Beds | Green | Beds confirmed safe for allocation |
| Delayed Turnovers | Red | Admissions where > 2h has elapsed since clinical readiness and bed is not yet safe |
| Stale Data | Orange | Admissions with at least one STALE record |
| Missing Data | Red | Admissions with at least one MISSING record |
| Conflicting Data | Red | Admissions with at least one CONFLICTING event |
| High-Priority Actions | Red | Open HIGH-priority follow-up actions |

### Primary Metric Hero

The most important section on the dashboard. Shows three boxes:

- **Baseline (Manual)** — Orange — Median delay in the manual/pre-prototype workflow
- **Target (−20%)** — Blue — The 20% reduction target
- **Measured Result** — Green — Actual median from this system

Below these boxes, a badge shows the improvement percentage and whether the target was met. All values come from live calculation against the synthetic dataset.

Detailed statistics (mean, median, P90, min, max) are shown below.

### Charts

Two side-by-side bar charts:
1. **Beds by Stage** — Shows how many admissions are in each workflow stage
2. **Data Quality Issues** — Shows count of each issue type (MISSING, STALE, CONFLICTING, INVALID_SEQUENCE, DUPLICATE, INVALID)

### Filter Bar

Persistent filters above the admission grid:
- Free-text search (patient, bed, facility)
- Facility dropdown
- Ward dropdown
- Stage dropdown
- Toggle buttons: Delayed / Stale / Missing / Conflicting
- Clear button

Filters apply in real time without page reload.

### Admission Grid

Cards for all matching admissions, sorted by escalated first, then by elapsed time descending.

Each card shows:
- Bed ID and stage badge
- Facility and ward
- Patient ID and acuity
- Readiness time
- Elapsed time since readiness (colour-coded: green <2h, amber 2–4h, red >4h)
- Freshness tag (FRESH / STALE / MISSING / CONFLICTING)
- Issue chips for each data quality problem
- ESCALATED badge if applicable
- Click to open detail modal

## Turnover Board

Kanban view across 6 columns:
1. Clinical Ready
2. Discharge Order
3. Awaiting Cleaning
4. Cleaning
5. Safety Check
6. Safe Available

Each column shows a count badge and lists all matching admissions as compact cards with elapsed time and issue chips. Delayed cards have a red left border. Escalated cards have a red background.

## Actions Panel

Three sections: High Priority / Medium Priority / Resolved.

Each action card shows:
- Issue text
- Owner
- Facility and bed
- Due date/time
- Status
- Escalation level
- Acknowledge / Resolve / Escalate buttons

High-priority unresolved actions remain visible until explicitly resolved.

## Error Analysis

Table with one row per error type explaining what happened, why it matters, how it was detected, how it was prevented from causing unsafe assumptions, and what follow-up was created.

Below the table, edge case cards for each of the 8 implemented failure scenarios with "View these cases →" link.

## Stakeholder Validation

Table showing synthetic usability results for all 6 roles across 6 questions.
Clearly labelled as synthetic validation, not real user research.
