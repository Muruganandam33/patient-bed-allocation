# Accessibility

## Design Principles

The dashboard is designed for users with limited digital literacy, including clinical staff who may not be technology-focused. The guiding principle is: **show meaning in text, never rely on colour alone.**

## Implemented Features

### Text Size
- Base font size: 16px (body text)
- Section headings: 18–22px
- KPI values: 36px
- Metric values: 28–36px
- All text sizes use CSS custom properties for easy adjustment

### Colour + Text Labels
Every status is shown with both a colour and a text label:

| Bad practice | Good practice (implemented) |
|-------------|----------------------------|
| Red dot | 🔴 ESCALATED |
| Green background | ✅ Safe Available |
| Orange text | ⏰ STALE — Last updated 6.0 hours ago |
| No indicator | ❌ MISSING — Cleaning completion not recorded |

### Freshness Always Shown as Text

```
FRESH    →  "Updated 30 minutes ago"
STALE    →  "STALE — Last updated 6.0 hours ago"
MISSING  →  "MISSING — No timestamp recorded"
INVALID  →  "INVALID — Timestamp is in the future"
```

### Icons + Text
Every button and label uses both an icon and a text label:
- ✅ Resolve (not just a checkmark)
- 🔴 Escalate (not just a red button)
- ⏰ Delayed (not just a colour change)
- 🏥 Facility (not just text)

### ARIA Roles and Landmarks
- `<header role="banner">` — top navigation
- `<main role="main">` — primary content area
- `<nav role="navigation" aria-label="Main navigation">` — nav bar
- `role="region" aria-label="..."` — all major sections
- `role="list"` / `role="listitem"` — admission grids and timelines
- `role="dialog" aria-modal="true"` — detail modal
- `aria-live="polite"` — main content area (announces updates to screen readers)
- `aria-live="assertive"` — error region
- `aria-label` on all controls, charts, and interactive elements
- `aria-pressed` on toggle buttons
- `aria-selected` on navigation tabs
- `aria-controls` linking nav buttons to content area

### Skip Navigation
A skip link is the first element in the page:
```html
<a href="#main-content" class="skip-link">Skip to main content</a>
```
Visible on keyboard focus, hidden otherwise.

### Keyboard Navigation
- All buttons, cards, and links are keyboard-reachable via Tab
- Cards trigger on both click and Enter keypress
- Modal closes on Escape or clicking the overlay
- Focus moves to the close button when a modal opens
- All focus states have a 3px solid outline (`outline: 3px solid #2563a8`)

### High Contrast Colour Scheme
| Use | Colour | Contrast vs white background |
|-----|--------|------------------------------|
| Primary text | #1e293b | 14.4:1 (AAA) |
| Primary action | #1a3a5c | 11.8:1 (AAA) |
| Danger / error | #b91c1c | 5.1:1 (AA) |
| Warning | #b45309 | 4.8:1 (AA) |
| Success | #0e7f3c | 5.3:1 (AA) |
| Muted text | #475569 | 7.2:1 (AA) |

### Simple Language
- "Awaiting Cleaning" not "Pending Sanitation Process"
- "Needs Immediate Attention" not "Critical Priority Queue"
- "Updated 30 minutes ago" not "Timestamp delta: 1800s"
- "Cleaning completion not recorded" not "CLEANING_COMPLETION_NULL"

### Large Buttons
All action buttons have minimum padding of 8px 16px, font size 14px, font weight 700.

### "Needs Attention" Section
A dedicated, prominently placed section at the top of the dashboard showing only items requiring immediate action. This gives users with limited literacy a single clear entry point.

### Error Messages
All error and issue messages are written in plain language:
- "MISSING — Discharge order not found — clinical team action required"
- "CONFLICTING — Bed state shows CLEANING IN PROGRESS but cleaning record is marked COMPLETED"
- "STALE — Last updated 6.0 hours ago"

### Minimal Navigation
Five top-level views only:
1. Dashboard
2. Turnover Board
3. Actions
4. Error Analysis
5. Stakeholder

No nested menus, no hidden dropdowns.

## Known Limitations

- Full WCAG 2.1 AA compliance has not been independently audited. Manual testing with assistive technologies is required to confirm compliance.
- Dynamic content updates (filter results) use `aria-live="polite"` but screen reader announcement timing depends on the client's assistive technology.
- Chart elements use `role="presentation"` and are supplemented with data tables; however, no dedicated accessible chart library is used.
