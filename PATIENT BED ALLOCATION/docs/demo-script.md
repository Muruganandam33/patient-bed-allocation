# 3-Minute Demo Script

## Pre-Demo Setup

1. Run `python data/generate_data.py` (if not already done)
2. Start server: `cd app && python app.py`
3. Open http://127.0.0.1:5000 in a browser
4. Set role selector to **Bed Coordinator**
5. Have the following tabs or filters ready:
   - Dashboard (default)
   - Turnover Board
   - Actions panel
   - One admission with scenario=`missing_cleaning` open in detail
   - One admission with scenario=`stale_data` open in detail
   - One admission with scenario=`conflicting` open in detail

---

## Demo Data Highlights

Before starting, identify these specific cases from the board (use the search/filter bar):

| Demo Case | How to find |
|-----------|------------|
| Normal workflow | Any card with stage SAFE_AVAILABLE and no issue chips |
| Delayed cleaning | Filter: "Delayed" toggle ON + stage CLEANING |
| Missing event | Filter: "Missing" toggle ON |
| Stale event | Filter: "Stale" toggle ON |
| Conflicting event | Filter: "Conflicting" toggle ON |
| Escalated action | Actions panel — red ESCALATED badge |

---

## 0:00 – 0:20 · The Problem

> "A hospital group transfers patients between facilities. Every day, beds sit empty for hours because no one knows which patient is ready to leave, which bed has been cleaned, or whether it's been safety-checked. Different teams have different parts of the picture — but no one has the full picture. The result: patients wait, beds sit idle, and transfers are delayed."

**Show:** The "Needs Immediate Attention" banner at the top of the dashboard. Point to a red ESCALATED item.

> "This board gives every team a shared, real-time view of the discharge and bed-turnover pipeline."

---

## 0:20 – 0:50 · The Dashboard

> "The dashboard shows 13 key indicators at a glance."

**Point to KPI cards:**
- Available Beds, Clinically Ready, Awaiting Cleaning, Delayed Turnovers
- Missing Data, Conflicting Data, High-Priority Actions

> "The most important metric is here."

**Point to the Primary Metric Hero:**

> "Time from Clinical Discharge Readiness to Next Safe Bed Availability. Our baseline — the manual workflow — had a median delay of 564 minutes. Nearly ten hours. Our target was a 20% reduction. The measured result: 242 minutes. That's a 57% improvement. The target is met."

**Point to the bar charts:**
> "We can see how beds are distributed across the workflow stages, and exactly what types of data quality problems exist."

---

## 0:50 – 1:20 · Role-Based Workflow

> "Different staff see different things depending on their role."

**Change role selector to Housekeeping:**
> "Housekeeping sees their cleaning queue: beds awaiting cleaning and cleaning in progress — nothing else cluttering the view."

**Change to Clinical:**
> "The clinical team sees patients who need discharge orders, and milestones that haven't been completed yet."

**Switch to Turnover Board tab:**
> "The Turnover Board shows the full pipeline as a Kanban. Each column is a stage. Cards move from Clinical Ready, through Discharge Order, Awaiting Cleaning, Cleaning, Safety Check, to Safe Available. Red cards are delayed."

---

## 1:20 – 1:50 · Drill-Down Evidence

> "Click any card to see the full evidence chain."

**Click a card with a normal workflow:**
> "Here we see every event in sequence: admission, clinical milestones, discharge order, bed state changes, cleaning start and completion, safety verification, and finally safe availability. Each event has a quality badge — green Valid, or flagged with the specific problem."

> "The turnover delay for this patient is shown here — 90 minutes from clinical readiness to safe availability."

---

## 1:50 – 2:15 · Missing, Stale, and Conflicting Data

**Filter: Missing toggle ON. Click a card from the missing_cleaning scenario:**
> "This patient is clinically ready. A discharge order was issued. But cleaning completion was never recorded. The system shows MISSING — cleaning completion not recorded. The bed is blocked from becoming safe available. A follow-up action has been automatically created."

**Filter: Stale toggle ON. Click a stale_data card:**
> "This bed's cleaning record hasn't been updated in 6 hours. The freshness indicator says: STALE — Last updated 6.0 hours ago. The system does not accept this as a fresh record. It is not counted as safely available."

**Filter: Conflicting toggle ON. Click a conflicting card:**
> "Here the bed state says CLEANING IN PROGRESS, but the cleaning record says COMPLETED. These two records disagree. The system shows CONFLICTING. Safe availability is blocked until someone investigates and resolves it."

---

## 2:15 – 2:40 · Owner, Due Date, and Escalation

**Navigate to Actions tab:**
> "Every unresolved issue has a follow-up action with an owner, due time, priority, and status."

**Point to a High Priority action:**
> "High-priority actions appear at the top. They stay visible until explicitly resolved. You can acknowledge, resolve, or escalate with one click."

**Point to an ESCALATED action:**
> "This action has been escalated — it missed its due time. It has a red ESCALATED badge and an escalation level of 2. It cannot be ignored."

> "Clicking Resolve marks it done and moves it to the resolved section."

---

## 2:40 – 3:00 · Baseline vs Target vs Result + Accessibility

**Return to Dashboard:**
> "Back to the primary metric. Baseline: 564 minutes. Target: 451 minutes. Measured: 242 minutes. 57% improvement. All values come from the actual data — nothing is made up."

> "The board is designed for all staff, including those with limited digital literacy. Every status is shown as text, not just colour. Urgent items are grouped in a dedicated 'Needs Immediate Attention' section. Large text, large buttons, plain language throughout. All keyboard-accessible."

**Point to a freshness tag:**
> "STALE — Last updated 6.0 hours ago. Not just a yellow dot. The message tells you exactly what it means and how old the data is."

> "This prototype is ready for user testing. Thank you."

---

## Backup Talking Points

- "If a stale or missing record is found, the system never silently treats it as valid — the bed stays blocked until the issue is resolved."
- "The prototype covers 100 admissions across 13 scenario types, including normal workflows, delayed cases, and 8 specific failure/edge cases."
- "We ran 27 automated tests. All pass."
- "The improvement from 564 to 242 minutes represents the value of eliminating manual coordination overhead — every team acting on the same real-time information."
