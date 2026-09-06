# User Workflow Map

## End-to-End Workflow

```
┌─────────────────────────────────────────────────────────────────────┐
│  STAGE            │  ACTOR              │  SYSTEM ACTION             │
├─────────────────────────────────────────────────────────────────────┤
│  1. Admission     │  Ward / Admin       │  Create admission record    │
│                   │                     │  Assign bed, set acuity     │
├─────────────────────────────────────────────────────────────────────┤
│  2. Clinical      │  Doctor / Nurse     │  Record milestones          │
│     Milestones    │                     │  (labs, imaging, specialist)│
├─────────────────────────────────────────────────────────────────────┤
│  3. Clinical      │  Doctor             │  Mark patient READY         │
│     Discharge     │                     │  ← PRIMARY METRIC STARTS   │
│     Readiness     │                     │  Board transitions to       │
│                   │                     │  CLINICAL_READY stage       │
├─────────────────────────────────────────────────────────────────────┤
│  4. Discharge     │  Doctor             │  Issue discharge order      │
│     Order         │                     │  Board transitions to       │
│                   │                     │  DISCHARGE_ORDER stage      │
├─────────────────────────────────────────────────────────────────────┤
│  5. Bed Turnover  │  Bed Coordinator    │  Assign bed to cleaning     │
│     Required      │                     │  Notify housekeeping        │
│                   │                     │  Board: AWAITING_CLEANING   │
├─────────────────────────────────────────────────────────────────────┤
│  6. Cleaning      │  Housekeeping       │  Start cleaning             │
│                   │                     │  Record start time          │
│                   │                     │  Board: CLEANING            │
│                   │                     │  Complete cleaning          │
│                   │                     │  Record completion time     │
├─────────────────────────────────────────────────────────────────────┤
│  7. Safety        │  Nurse / Coord.     │  Verify bed is safe         │
│     Verification  │                     │  Record verification        │
│                   │                     │  Board: AWAITING_SAFETY_CHECK│
├─────────────────────────────────────────────────────────────────────┤
│  8. Safe Bed      │  System             │  Only when ALL are true:    │
│     Available     │                     │  - Cleaning completed       │
│                   │                     │  - Safety PASSED            │
│                   │                     │  - No CONFLICTING issues    │
│                   │                     │  Board: SAFE_AVAILABLE      │
│                   │                     │  ← PRIMARY METRIC ENDS     │
├─────────────────────────────────────────────────────────────────────┤
│  9. Bed           │  Transfer Coord.    │  Allocate bed to patient    │
│     Allocation /  │  Bed Coordinator   │  Arrange transfer           │
│     Transfer      │                     │  Board: OCCUPIED (new adm.) │
└─────────────────────────────────────────────────────────────────────┘
```

## Role-Specific Workflows

### Bed Coordinator

1. Open dashboard — see "Needs Immediate Attention" banner
2. Review delayed beds (elapsed > 2 hours since readiness)
3. Check stale/missing data warnings
4. Assign or escalate follow-up actions
5. Use Turnover Board to see bottlenecks by stage
6. Filter by facility to focus on a specific site

### Doctor / Clinical Team

1. Open dashboard, select Clinical role
2. View patients with clinical milestones in progress
3. See which patients are ready but lack a discharge order
4. Identify missing clinical information (e.g. specialist clearance missing)
5. Drill down to evidence timeline to verify all milestones recorded

### Nurse / Ward Staff

1. Open dashboard, select Nurse role
2. See ward discharge status for their ward
3. View pending tasks for their patients
4. Check freshness of bed and cleaning records
5. Record or confirm safety verification

### Housekeeping

1. Open Turnover Board, select Housekeeping role
2. See AWAITING_CLEANING queue
3. See CLEANING in progress
4. See overdue cleaning (elapsed > 90 min)
5. Mark cleaning complete to advance the workflow

### Transfer Coordinator

1. Open dashboard, select Transfer role
2. See transfer-required patients
3. See beds in SAFE_AVAILABLE stage
4. Identify transfer delays with elapsed time
5. Create or escalate transfer actions

### Administrator / Management

1. Open dashboard, select Admin role
2. Review primary KPI and baseline vs target vs result
3. See improvement percentage
4. Review error analysis — missing/stale/conflicting counts
5. Review stakeholder validation tab

## Data Entry Points (Simulated in Prototype)

In a production system, these would be integrated with:
- Electronic Patient Record (EPR) for clinical milestones and discharge orders
- Bed Management System for bed states
- Housekeeping Work Order System for cleaning events
- Facilities Management System for safety verifications

In this prototype, all data is generated synthetically and loaded on startup.
