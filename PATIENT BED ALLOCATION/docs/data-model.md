# Data Model

## Overview

The data model represents the full discharge-to-bed-availability workflow as a chain of related events. Each admission links to milestones, a discharge order, cleaning events, bed state events, and a safety verification. A bed is only safe when all conditions are met.

## Entities

### ADMISSION

The root record. Each admission represents one patient occupying one bed.

| Field | Type | Description |
|-------|------|-------------|
| admission_id | string | Unique identifier (e.g. ADM-A1B2C3) |
| patient_id | string | Patient identifier |
| facility_id | string | Facility name |
| ward | string | Ward within the facility |
| bed_id | string | Bed identifier |
| admission_time | ISO datetime | When patient was admitted |
| expected_discharge_date | ISO datetime | Clinically expected discharge |
| acuity | enum | LOW / MEDIUM / HIGH / CRITICAL |
| transfer_required | boolean | Whether inter-facility transfer is needed |
| scenario | string | Synthetic scenario tag (for testing) |

### CLINICAL MILESTONE

Records each clinical step completed before discharge. Multiple milestones per admission.

| Field | Type | Description |
|-------|------|-------------|
| milestone_id | string | Unique identifier |
| admission_id | string | Foreign key to ADMISSION |
| milestone_type | enum | labs_reviewed, imaging_reviewed, specialist_cleared, medication_reconciled, discharge_summary_written, family_notified, transport_arranged, clinical_readiness_confirmed |
| milestone_time | ISO datetime | When milestone was achieved |
| clinical_readiness_status | enum | PENDING / READY |
| recorded_by | string | Staff member who recorded it |

The milestone with `clinical_readiness_status = READY` and `milestone_type = clinical_readiness_confirmed` is the **primary metric start point**.

### DISCHARGE ORDER

The formal order to discharge. One per admission (may be missing).

| Field | Type | Description |
|-------|------|-------------|
| discharge_order_id | string | Unique identifier |
| admission_id | string | Foreign key to ADMISSION |
| discharge_order_time | ISO datetime | When order was issued |
| discharge_status | enum | ISSUED / CANCELLED / PENDING |
| priority | enum | ROUTINE / URGENT / STAT |

### CLEANING EVENT

Records the cleaning of a bed after discharge. Linked to the bed, not the admission.

| Field | Type | Description |
|-------|------|-------------|
| cleaning_event_id | string | Unique identifier |
| bed_id | string | Which bed was cleaned |
| start_time | ISO datetime | When cleaning started |
| completion_time | ISO datetime | When cleaning completed |
| cleaning_status | enum | COMPLETED / IN_PROGRESS / STALE / INVALID_TIMESTAMP |
| assigned_to | string | Housekeeping team/person |

### BED STATE EVENT

Tracks the state of a bed over time. Multiple events per bed forming a history.

| Field | Type | Description |
|-------|------|-------------|
| bed_state_id | string | Unique identifier |
| bed_id | string | Which bed |
| facility_id | string | Facility |
| ward | string | Ward |
| timestamp | ISO datetime | When state was recorded |
| bed_state | enum | See valid states below |
| safety_check_status | enum | PENDING / PASSED / FAILED |

**Valid bed states:**
```
OCCUPIED → DISCHARGE_PENDING → AWAITING_CLEANING → CLEANING → AWAITING_SAFETY_CHECK → SAFE_AVAILABLE
                                                                                          ↓
                                                                                       UNAVAILABLE
```

Invalid state transitions are detected as INVALID_SEQUENCE issues.

### SAFETY VERIFICATION

Records the formal safety check before a bed is released. One per admission.

| Field | Type | Description |
|-------|------|-------------|
| safety_id | string | Unique identifier |
| bed_id | string | Which bed |
| admission_id | string | Foreign key to ADMISSION |
| verified_by | string | Staff member who verified |
| verification_time | ISO datetime | When verified |
| verification_status | enum | PASSED / FAILED / MISSING |
| notes | string | Free text notes |

### ACTION

Follow-up action created for an unresolved issue. One or more per admission.

| Field | Type | Description |
|-------|------|-------------|
| action_id | string | Unique identifier |
| admission_id | string | Foreign key to ADMISSION |
| issue | string | Description of the issue |
| owner | string | Assigned staff member |
| priority | enum | LOW / MEDIUM / HIGH |
| due_datetime | ISO datetime | When action is due |
| status | enum | OPEN / ACKNOWLEDGED / RESOLVED / ESCALATED |
| escalation_level | integer | 0 = not escalated, 1+ = escalation level |
| escalated | boolean | True if currently escalated |
| created_at | ISO datetime | When action was created |
| acknowledged_at | ISO datetime | When acknowledged (nullable) |
| resolved_at | ISO datetime | When resolved (nullable) |

## Safe Availability Rule

A bed is **only** considered SAFE_AVAILABLE when ALL of the following are true:

```python
cleaning is not None
AND cleaning.completion_time is not None
AND cleaning.completion_time > cleaning.start_time
AND (NOW - cleaning.completion_time) < 4 hours   # freshness check
AND cleaning.cleaning_status not in ("STALE", "INVALID_TIMESTAMP")
AND safety_verification.verification_status == "PASSED"
AND latest bed_state == "SAFE_AVAILABLE"
AND no active CONFLICTING issues
```

Any violation returns False with an explicit reason string.

## Data Quality States

| State | Meaning | Action |
|-------|---------|--------|
| VALID | Record passes all checks | None required |
| FRESH | Timestamp within 4 hours | None required |
| STALE | Timestamp older than 4 hours | Re-verify, show warning |
| MISSING | Required field or record absent | Block workflow, create action |
| CONFLICTING | Two records disagree | Block safe availability, create action |
| INVALID | Value fails validity check | Block usage, create action |
| INVALID_SEQUENCE | Events in wrong order | Flag, exclude from metrics |
| DUPLICATE | Same ID appears more than once | Exclude duplicates from calculations |
