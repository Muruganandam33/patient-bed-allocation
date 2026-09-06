/* ═══════════════════════════════════════════════════════
   Discharge-Readiness Bed-Turnover Coordination Board
   Main application JavaScript
   ═══════════════════════════════════════════════════════ */

// ── State ──────────────────────────────────────────────────────────────────
const State = {
  currentView: 'dashboard',
  currentRole: 'coordinator',
  admissions: [],
  dashboard: null,
  experiment: null,
  validation: null,
  errorAnalysis: null,
  actions: [],
  facilities: [],
  wards: [],
  stages: [],
  filters: {
    facility: '', ward: '', stage: '', search: '',
    delayed: false, stale: false, missing: false, conflicting: false,
  },
};

// ── Helpers ────────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const esc = s => String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

function fmtMinutes(min) {
  if (min === null || min === undefined) return '—';
  if (min < 60) return `${Math.round(min)} min`;
  const h = Math.floor(min / 60);
  const m = Math.round(min % 60);
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

function fmtTs(ts) {
  if (!ts) return '—';
  try {
    const d = new Date(ts);
    return d.toLocaleString('en-GB', {
      day:'2-digit', month:'short', hour:'2-digit', minute:'2-digit'
    });
  } catch { return ts; }
}

function stageLabel(stage) {
  const map = {
    ADMITTED: '🏥 Admitted',
    CLINICAL_READY: '✅ Clinically Ready',
    DISCHARGE_ORDER: '📋 Discharge Order',
    AWAITING_CLEANING: '⏳ Awaiting Cleaning',
    CLEANING: '🧹 Cleaning',
    SAFETY_CHECK: '🔍 Safety Check',
    SAFE_AVAILABLE: '🟢 Safe Available',
    UNAVAILABLE: '🚫 Unavailable',
  };
  return map[stage] || stage;
}

function priorityIcon(p) {
  return { HIGH: '🔴', MEDIUM: '🟡', LOW: '🟢' }[p] || '⚪';
}

function qualityBadge(q) {
  const cfg = {
    VALID:          ['✔ Valid',         '#dcfce7','#166534'],
    MISSING:        ['⚠ Missing',       '#fee2e2','#7f1d1d'],
    STALE:          ['⏰ Stale',         '#fef3c7','#92400e'],
    CONFLICTING:    ['⚡ Conflicting',   '#ede9fe','#4c1d95'],
    INVALID:        ['✖ Invalid',        '#fee2e2','#b91c1c'],
    INVALID_SEQUENCE:['⚡ Invalid Seq',  '#fce7f3','#831843'],
    DUPLICATE:      ['⊙ Duplicate',     '#e0f2fe','#0c4a6e'],
    NOT_YET:        ['⏸ Not Yet',       '#f1f5f9','#475569'],
  };
  const [label, bg, color] = cfg[q] || ['?','#f1f5f9','#475569'];
  return `<span class="tl-quality-badge" style="background:${bg};color:${color}">${label}</span>`;
}

// ── API calls ──────────────────────────────────────────────────────────────
async function apiFetch(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

async function apiPost(url, body) {
  const res = await fetch(url, {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(body),
  });
  return res.json();
}

// ── Load data ──────────────────────────────────────────────────────────────
async function loadDashboard() {
  State.dashboard = await apiFetch('/api/dashboard');
  State.experiment = await apiFetch('/api/experiment');
  State.validation = await apiFetch('/api/validation');
}

async function loadAdmissions() {
  const params = new URLSearchParams();
  if (State.filters.facility) params.set('facility', State.filters.facility);
  if (State.filters.ward)     params.set('ward',     State.filters.ward);
  if (State.filters.stage)    params.set('stage',    State.filters.stage);
  if (State.filters.search)   params.set('search',   State.filters.search);
  if (State.filters.delayed)  params.set('delayed',  'true');
  if (State.filters.stale)    params.set('stale',    'true');
  if (State.filters.missing)  params.set('missing',  'true');
  if (State.filters.conflicting) params.set('conflicting','true');
  params.set('role', roleApiKey(State.currentRole));
  State.admissions = await apiFetch('/api/admissions?' + params);
}

async function loadActions() {
  State.actions = await apiFetch('/api/actions');
}

async function loadFacilities() {
  const d = await apiFetch('/api/facilities');
  State.facilities = d.facilities;
  State.wards = d.wards;
  State.stages = d.stages;
  populateFilterDropdowns();
}

async function loadErrorAnalysis() {
  State.errorAnalysis = await apiFetch('/api/error-analysis');
}

function roleApiKey(role) {
  const map = {
    coordinator: 'coordinator',
    clinical: 'clinical',
    nurse: 'nurse',
    housekeeping: 'housekeeping',
    transfer: 'transfer',
    admin: 'admin',
  };
  return map[role] || '';
}

// ── Navigation ─────────────────────────────────────────────────────────────
function navigate(view) {
  State.currentView = view;
  document.querySelectorAll('.nav-links button').forEach(b => {
    b.classList.toggle('active', b.dataset.view === view);
    b.setAttribute('aria-selected', b.dataset.view === view);
  });
  renderCurrentView();
}

// ── Role ───────────────────────────────────────────────────────────────────
function setRole(role) {
  State.currentRole = role;
  renderCurrentView();
}

const ROLE_INFO = {
  coordinator: {
    icon: '🗂️',
    label: 'Bed Coordinator',
    description: 'Showing: delayed beds, discharge-ready cases, bottlenecks, stale/missing data and urgent actions.',
  },
  clinical: {
    icon: '🩺',
    label: 'Doctor / Clinical Team',
    description: 'Showing: clinical readiness, milestones, discharge orders and missing clinical information.',
  },
  nurse: {
    icon: '👩‍⚕️',
    label: 'Nurse / Ward Staff',
    description: 'Showing: ward discharge status, pending tasks and next actions.',
  },
  housekeeping: {
    icon: '🧹',
    label: 'Housekeeping',
    description: 'Showing: cleaning queue, cleaning progress and overdue cleaning tasks.',
  },
  transfer: {
    icon: '🚑',
    label: 'Transfer Coordinator',
    description: 'Showing: transfer-ready patients, expected bed availability and transfer delays.',
  },
  admin: {
    icon: '📊',
    label: 'Administrator / Management',
    description: 'Showing: full KPIs, baseline vs target vs result, facility/ward summary and trends.',
  },
};

// ── Render dispatcher ──────────────────────────────────────────────────────
async function renderCurrentView() {
  const main = $('main-content');
  main.innerHTML = '<div class="loading-spinner" aria-live="polite">Loading...</div>';
  try {
    await loadAdmissions();
    switch (State.currentView) {
      case 'dashboard':  await loadDashboard(); renderDashboard(main); break;
      case 'board':      renderBoard(main); break;
      case 'actions':    await loadActions(); renderActions(main); break;
      case 'errors':     await loadErrorAnalysis(); renderErrorAnalysis(main); break;
      case 'stakeholder':renderStakeholder(main); break;
      default:           renderDashboard(main);
    }
  } catch (err) {
    main.innerHTML = `<div class="needs-attention" role="alert">
      <h3>⚠ Error loading data</h3>
      <p>${esc(err.message)}</p>
    </div>`;
  }
}

// ══════════════════════════════════════════════════════════════════════════
// DASHBOARD
// ══════════════════════════════════════════════════════════════════════════
function renderDashboard(container) {
  const d = State.dashboard;
  const exp = State.experiment;
  const role = State.currentRole;
  const ri = ROLE_INFO[role];

  const base = exp?.baseline?.median;
  const tgt  = exp?.target_median_minutes;
  const res  = exp?.measured?.median;
  const impv = exp?.improvement_pct;
  const metTarget = exp?.target_met;

  // Needs attention — escalated / missing / conflicting
  const needsAttention = State.admissions.filter(v =>
    v.escalated || v.issue_codes?.includes('CONFLICTING') || v.issue_codes?.includes('MISSING')
  ).slice(0, 5);

  container.innerHTML = `
    <div class="main-container">
      <div class="role-banner" role="note" aria-label="Current role: ${esc(ri.label)}">
        <span style="font-size:24px">${ri.icon}</span>
        <div>
          <strong>${esc(ri.label)}</strong><br>
          <span style="font-size:13px;opacity:.85">${esc(ri.description)}</span>
        </div>
      </div>

      ${needsAttention.length ? `
      <div class="needs-attention" role="alert" aria-label="Items needing immediate attention">
        <h3>🚨 Needs Immediate Attention (${needsAttention.length})</h3>
        ${needsAttention.map(v => `
          <div class="attention-item">
            <span style="font-size:18px">${v.escalated ? '🔴' : '⚠'}</span>
            <div>
              <strong>${esc(v.bed_id)}</strong> — ${esc(v.ward)}, ${esc(v.facility_id)}
              &nbsp;${(v.issue_codes||[]).map(c=>`<span class="chip ${esc(c)}">${esc(c)}</span>`).join('')}
              &nbsp;<button class="btn btn-sm btn-outline" onclick="openDetail('${esc(v.admission_id)}')">View Detail →</button>
            </div>
          </div>
        `).join('')}
      </div>` : ''}

      <h2 class="section-title">📊 Dashboard Overview</h2>

      <div class="kpi-grid" role="region" aria-label="Key performance indicators">
        ${kpiCard(d.total_beds, 'Total Beds', 'info')}
        ${kpiCard(d.available_beds, 'Available Beds', 'success')}
        ${kpiCard(d.clinically_ready_discharges, 'Clinically Ready', 'info')}
        ${kpiCard(d.pending_discharge_orders, 'Pending Discharge Orders', '')}
        ${kpiCard(d.awaiting_cleaning, 'Awaiting Cleaning', 'warning')}
        ${kpiCard(d.cleaning_in_progress, 'Cleaning in Progress', 'warning')}
        ${kpiCard(d.awaiting_safety_check, 'Awaiting Safety Check', 'warning')}
        ${kpiCard(d.safe_available_beds, 'Safe Available Beds', 'success')}
        ${kpiCard(d.delayed_turnovers, 'Delayed Turnovers', 'danger')}
        ${kpiCard(d.stale_data_count, 'Stale Data', 'warning')}
        ${kpiCard(d.missing_data_count, 'Missing Data', 'danger')}
        ${kpiCard(d.conflicting_data_count, 'Conflicting Data', 'danger')}
        ${kpiCard(d.high_priority_unresolved, 'High-Priority Actions', 'danger')}
      </div>

      <!-- PRIMARY METRIC -->
      <div class="metric-hero" role="region" aria-label="Primary metric: Turnover Coordination Delay">
        <h2>⏱️ Primary Metric: Time from Clinical Discharge Readiness to Next Safe Bed Availability</h2>
        <div class="metric-row">
          <div class="metric-box baseline">
            <div class="m-label">📌 Baseline (Manual)</div>
            <div class="m-value">${base !== null && base !== undefined ? fmtMinutes(base) : '—'}</div>
            <div class="m-unit">Median delay — manual workflow</div>
          </div>
          <div class="metric-box target">
            <div class="m-label">🎯 Target (−20%)</div>
            <div class="m-value">${tgt !== null && tgt !== undefined ? fmtMinutes(tgt) : '—'}</div>
            <div class="m-unit">20% reduction in median delay</div>
          </div>
          <div class="metric-box result">
            <div class="m-label">📈 Measured Result</div>
            <div class="m-value">${res !== null && res !== undefined ? fmtMinutes(res) : '—'}</div>
            <div class="m-unit">Actual median — this system</div>
          </div>
        </div>
        <div style="text-align:center">
          ${impv !== null && impv !== undefined
            ? `<span class="improvement-badge ${metTarget ? '' : 'missed'}"
                 role="status" aria-label="Improvement: ${impv}% ${metTarget ? 'Target Met' : 'Target Not Met'}">
                 ${impv > 0 ? '▼' : '▲'} ${Math.abs(impv)}% improvement
                 &nbsp;${metTarget ? '✅ Target Met' : '⚠ Target Not Met'}
               </span>`
            : '<span class="improvement-badge missed">Insufficient data for calculation</span>'
          }
        </div>
        <div style="margin-top:16px">
          <strong>Detailed statistics (measured):</strong>
          <div class="metric-row" style="margin-top:8px">
            ${statBox('Mean',   fmtMinutes(exp?.measured?.mean))}
            ${statBox('Median', fmtMinutes(exp?.measured?.median))}
            ${statBox('P90',    fmtMinutes(exp?.measured?.p90))}
            ${statBox('Min',    fmtMinutes(exp?.measured?.min))}
            ${statBox('Max',    fmtMinutes(exp?.measured?.max))}
          </div>
        </div>
      </div>

      <!-- CHARTS -->
      <div class="charts-row">
        ${renderStageChart()}
        ${renderIssueChart()}
      </div>

      <!-- FILTER + ADMISSION LIST -->
      ${renderFilterBar()}
      <h3 class="section-title" style="font-size:18px">Bed / Admission Cards</h3>
      <div class="board-grid" id="admission-grid" role="list" aria-label="Admission cards">
        ${renderAdmissionCards(State.admissions)}
      </div>
    </div>
  `;
  attachFilterListeners();
}

function kpiCard(val, label, type) {
  return `<div class="kpi-card ${type}" role="figure" aria-label="${label}: ${val}">
    <div class="kpi-value">${val ?? '—'}</div>
    <div class="kpi-label">${label}</div>
  </div>`;
}

function statBox(label, val) {
  return `<div class="metric-box">
    <div class="m-label">${label}</div>
    <div class="m-value" style="font-size:20px;color:#1a3a5c">${val}</div>
  </div>`;
}

function renderStageChart() {
  const stageCounts = {};
  State.admissions.forEach(v => {
    stageCounts[v.stage] = (stageCounts[v.stage] || 0) + 1;
  });
  const maxVal = Math.max(...Object.values(stageCounts), 1);
  const colours = {
    ADMITTED:'#94a3b8', CLINICAL_READY:'#3b82f6', DISCHARGE_ORDER:'#0ea5e9',
    AWAITING_CLEANING:'#f59e0b', CLEANING:'#f97316', SAFETY_CHECK:'#8b5cf6',
    SAFE_AVAILABLE:'#22c55e', UNAVAILABLE:'#ef4444',
  };
  const rows = Object.entries(stageCounts).map(([s, n]) =>
    `<div class="bar-row">
      <div class="bar-label">${esc(stageLabel(s).replace(/^[^\s]+\s/,''))}</div>
      <div class="bar-fill-wrap" role="presentation">
        <div class="bar-fill" style="width:${Math.round(n/maxVal*100)}%;background:${colours[s]||'#94a3b8'}"></div>
      </div>
      <div class="bar-value">${n}</div>
    </div>`
  ).join('');
  return `<div class="chart-box"><h3>📊 Beds by Stage</h3><div class="bar-chart">${rows}</div></div>`;
}

function renderIssueChart() {
  const d = State.validation || {};
  const ic = d.issue_counts || {};
  const items = [
    {label:'Missing',       val: ic.MISSING     || 0, color:'#ef4444'},
    {label:'Stale',         val: ic.STALE        || 0, color:'#f59e0b'},
    {label:'Conflicting',   val: ic.CONFLICTING  || 0, color:'#8b5cf6'},
    {label:'Invalid Seq',   val: ic.INVALID_SEQUENCE||0, color:'#ec4899'},
    {label:'Duplicate',     val: ic.DUPLICATE    || 0, color:'#0ea5e9'},
    {label:'Invalid',       val: ic.INVALID      || 0, color:'#f97316'},
  ];
  const maxVal = Math.max(...items.map(i => i.val), 1);
  const rows = items.map(i =>
    `<div class="bar-row">
      <div class="bar-label">${esc(i.label)}</div>
      <div class="bar-fill-wrap">
        <div class="bar-fill" style="width:${Math.round(i.val/maxVal*100)}%;background:${i.color}"></div>
      </div>
      <div class="bar-value">${i.val}</div>
    </div>`
  ).join('');
  return `<div class="chart-box"><h3>⚠ Data Quality Issues</h3><div class="bar-chart">${rows}</div></div>`;
}

// ══════════════════════════════════════════════════════════════════════════
// BOARD (Kanban)
// ══════════════════════════════════════════════════════════════════════════
function renderBoard(container) {
  const ri = ROLE_INFO[State.currentRole];
  const stages = [
    { key: 'CLINICAL_READY',    label: 'Clinical Ready',   color: '#3b82f6' },
    { key: 'DISCHARGE_ORDER',   label: 'Discharge Order',  color: '#0ea5e9' },
    { key: 'AWAITING_CLEANING', label: 'Awaiting Cleaning',color: '#f59e0b' },
    { key: 'CLEANING',          label: 'Cleaning',         color: '#f97316' },
    { key: 'SAFETY_CHECK',      label: 'Safety Check',     color: '#8b5cf6' },
    { key: 'SAFE_AVAILABLE',    label: 'Safe Available',   color: '#22c55e' },
  ];

  const byStage = {};
  stages.forEach(s => { byStage[s.key] = []; });
  State.admissions.forEach(v => {
    if (byStage[v.stage]) byStage[v.stage].push(v);
    else if (v.stage === 'ADMITTED') { /* skip */ }
  });

  container.innerHTML = `
    <div class="main-container">
      <div class="role-banner">
        <span style="font-size:24px">${ri.icon}</span>
        <div><strong>${esc(ri.label)}</strong><br>
        <span style="font-size:13px;opacity:.85">${esc(ri.description)}</span></div>
      </div>
      <h2 class="section-title">🗂️ Bed Turnover Coordination Board</h2>
      ${renderFilterBar()}
      <div class="kanban-wrapper" role="region" aria-label="Bed turnover board">
        ${stages.map(s => `
          <div class="kanban-col" aria-label="Stage: ${s.label}">
            <div class="kanban-col-header" style="color:${s.color}">
              <span>${esc(s.label)}</span>
              <span style="background:${s.color};color:#fff;border-radius:12px;padding:1px 8px;font-size:12px">
                ${byStage[s.key].length}
              </span>
            </div>
            ${byStage[s.key].length === 0
              ? '<div style="color:#94a3b8;font-size:13px;text-align:center;padding:12px">No beds</div>'
              : byStage[s.key].map(v => renderKanbanCard(v)).join('')
            }
          </div>
        `).join('')}
      </div>
    </div>
  `;
  attachFilterListeners();
}

function renderKanbanCard(v) {
  const delayed = v.elapsed_since_readiness_min > 120 && v.stage !== 'SAFE_AVAILABLE';
  const issueChips = (v.issue_codes || []).slice(0, 3)
    .map(c => `<span class="chip ${esc(c)}" aria-label="Issue: ${esc(c)}">${esc(c)}</span>`).join('');

  return `<div class="kanban-card ${delayed ? 'delayed' : ''} ${v.escalated ? 'escalated' : ''}"
              role="button" tabindex="0"
              aria-label="Bed ${v.bed_id}, ${v.ward}, ${v.stage}${delayed ? ', DELAYED' : ''}"
              onclick="openDetail('${esc(v.admission_id)}')"
              onkeydown="if(event.key==='Enter')openDetail('${esc(v.admission_id)}')">
    <div style="display:flex;justify-content:space-between;align-items:flex-start">
      <strong style="font-size:15px">${esc(v.bed_id)}</strong>
      <span style="font-size:11px;font-weight:700;color:#64748b">${esc(v.acuity || '')}</span>
    </div>
    <div style="font-size:12px;color:#475569;margin:3px 0">${esc(v.ward)} · ${esc(v.facility_id?.split(' ')[0])}</div>
    ${v.elapsed_since_readiness_min != null
      ? `<div class="elapsed-badge ${v.elapsed_since_readiness_min > 240 ? 'danger' : v.elapsed_since_readiness_min > 120 ? 'warning' : 'ok'}">
           ⏱ ${fmtMinutes(v.elapsed_since_readiness_min)} since readiness
         </div>` : ''}
    <div style="margin-top:6px">${issueChips}</div>
    ${v.escalated ? '<div class="chip ESCALATED" style="margin-top:4px">🔴 ESCALATED</div>' : ''}
    <div class="freshness-tag ${v.freshness_status}" style="margin-top:6px;font-size:11px">
      ${v.freshness_text}
    </div>
  </div>`;
}

// ══════════════════════════════════════════════════════════════════════════
// ADMISSION CARDS (grid view)
// ══════════════════════════════════════════════════════════════════════════
function renderAdmissionCards(admissions) {
  if (!admissions.length) {
    return '<div class="empty-state">No admissions match the current filters.</div>';
  }
  return admissions.map(v => {
    const delayed = v.elapsed_since_readiness_min > 120 && v.stage !== 'SAFE_AVAILABLE';
    return `
    <div class="bed-card ${v.escalated ? 'escalated' : ''} ${v.has_issues ? 'has-issues' : ''}"
         role="listitem button" tabindex="0"
         aria-label="Bed ${v.bed_id}, ${v.stage}${delayed ? ', DELAYED' : ''}"
         onclick="openDetail('${esc(v.admission_id)}')"
         onkeydown="if(event.key==='Enter')openDetail('${esc(v.admission_id)}')">
      <div class="card-header">
        <span class="bed-id">${esc(v.bed_id)}</span>
        <span class="stage-badge stage-${esc(v.stage)}">${esc(stageLabel(v.stage))}</span>
      </div>
      <div class="info-row">🏥 <strong>${esc(v.facility_id)}</strong></div>
      <div class="info-row">🏠 Ward: <strong>${esc(v.ward)}</strong></div>
      <div class="info-row">👤 Patient: <strong>${esc(v.patient_id)}</strong></div>
      <div class="info-row">⚡ Acuity: <strong>${esc(v.acuity)}</strong></div>
      ${v.readiness_time
        ? `<div class="info-row">✅ Ready: <strong>${fmtTs(v.readiness_time)}</strong></div>` : ''}
      ${v.elapsed_since_readiness_min != null
        ? `<div class="elapsed-badge ${v.elapsed_since_readiness_min > 240 ? 'danger' : v.elapsed_since_readiness_min > 120 ? 'warning' : 'ok'}">
             ⏱ ${fmtMinutes(v.elapsed_since_readiness_min)} since readiness
           </div>` : ''}
      <div class="freshness-tag ${esc(v.freshness_status)}">${esc(v.freshness_text)}</div>
      ${(v.issue_codes || []).length
        ? `<div class="issue-chips" aria-label="Data quality issues">
             ${v.issue_codes.map(c => `<span class="chip ${esc(c)}" aria-label="${esc(c)} issue">${esc(c)}</span>`).join('')}
           </div>` : ''}
      ${v.escalated ? '<div class="chip ESCALATED" style="margin-top:6px">🔴 ESCALATED — Click to view</div>' : ''}
      <div style="margin-top:8px;font-size:13px;color:#0369a1;font-weight:600">
        👁 Click to view details →
      </div>
    </div>`;
  }).join('');
}

// ══════════════════════════════════════════════════════════════════════════
// ACTIONS
// ══════════════════════════════════════════════════════════════════════════
function renderActions(container) {
  const ri = ROLE_INFO[State.currentRole];
  const high = State.actions.filter(a => a.priority === 'HIGH' && a.status !== 'RESOLVED');
  const medium = State.actions.filter(a => a.priority === 'MEDIUM' && a.status !== 'RESOLVED');
  const resolved = State.actions.filter(a => a.status === 'RESOLVED');

  container.innerHTML = `
    <div class="main-container">
      <div class="role-banner">
        <span style="font-size:24px">${ri.icon}</span>
        <div><strong>${esc(ri.label)}</strong></div>
      </div>
      <h2 class="section-title">📋 Follow-Up Actions & Escalations</h2>
      <div style="display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap">
        <div class="kpi-card danger"><div class="kpi-value">${high.length}</div><div class="kpi-label">High Priority Open</div></div>
        <div class="kpi-card warning"><div class="kpi-value">${medium.length}</div><div class="kpi-label">Medium Priority Open</div></div>
        <div class="kpi-card success"><div class="kpi-value">${resolved.length}</div><div class="kpi-label">Resolved</div></div>
      </div>

      ${high.length > 0 ? `
        <h3 style="font-size:16px;font-weight:700;color:#b91c1c;margin-bottom:10px">🔴 High Priority — Requires Immediate Action</h3>
        ${high.map(a => renderActionCard(a)).join('')}
      ` : ''}

      ${medium.length > 0 ? `
        <h3 style="font-size:16px;font-weight:700;color:#b45309;margin:16px 0 10px">🟡 Medium Priority</h3>
        ${medium.map(a => renderActionCard(a)).join('')}
      ` : ''}

      ${resolved.length > 0 ? `
        <h3 style="font-size:16px;font-weight:700;color:#166534;margin:16px 0 10px">✅ Resolved</h3>
        ${resolved.map(a => renderActionCard(a)).join('')}
      ` : ''}
    </div>
  `;
}

function renderActionCard(a) {
  const isEscalated = a.escalated || a.status === 'ESCALATED';
  const isResolved = a.status === 'RESOLVED';
  return `
  <div class="action-card ${a.priority} ${a.status}" id="action-${esc(a.action_id)}"
       role="region" aria-label="Action: ${esc(a.issue)}">
    <div class="action-title">
      ${priorityIcon(a.priority)} ${esc(a.issue)}
      ${isEscalated ? '<span class="chip ESCALATED">🔴 ESCALATED</span>' : ''}
    </div>
    <div class="action-meta">
      <span>👤 Owner: <strong>${esc(a.owner || 'Unassigned')}</strong></span>
      <span>🏥 Facility: <strong>${esc(a.facility || '—')}</strong></span>
      <span>🛏 Bed: <strong>${esc(a.bed_id || '—')}</strong></span>
      <span>⏰ Due: <strong>${fmtTs(a.due_datetime)}</strong></span>
      <span>📊 Status: <strong>${esc(a.status)}</strong></span>
      <span>🔺 Escalation Level: <strong>${a.escalation_level || 0}</strong></span>
    </div>
    ${!isResolved ? `
    <div class="action-buttons">
      <button class="btn btn-outline btn-sm" onclick="updateAction('${esc(a.action_id)}','ACKNOWLEDGED')"
              aria-label="Acknowledge action">✓ Acknowledge</button>
      <button class="btn btn-success btn-sm" onclick="updateAction('${esc(a.action_id)}','RESOLVED')"
              aria-label="Mark as resolved">✅ Resolve</button>
      <button class="btn btn-danger btn-sm" onclick="updateAction('${esc(a.action_id)}','ESCALATED')"
              aria-label="Escalate action">🔴 Escalate</button>
    </div>` : '<div style="color:#166534;font-weight:700">✅ Resolved</div>'}
  </div>`;
}

async function updateAction(actionId, status) {
  const result = await apiPost(`/api/actions/${actionId}`, { status });
  if (result.ok) {
    await loadActions();
    renderActions($('main-content'));
  }
}

// ══════════════════════════════════════════════════════════════════════════
// ERROR ANALYSIS
// ══════════════════════════════════════════════════════════════════════════
function renderErrorAnalysis(container) {
  const ea = State.errorAnalysis;
  if (!ea) { container.innerHTML = '<div class="loading-spinner">Loading...</div>'; return; }

  container.innerHTML = `
    <div class="main-container">
      <h2 class="section-title">🔍 Error Analysis & Data Quality Report</h2>
      <div class="kpi-grid">
        ${kpiCard(ea.total_records,         'Total Admissions', 'info')}
        ${kpiCard(ea.valid_records,         'Valid Records',    'success')}
        ${kpiCard(ea.admissions_with_issues,'With Issues',      'warning')}
        ${kpiCard(ea.pct_affected + '%',    '% Affected',       'danger')}
      </div>

      <table class="data-table" role="table" aria-label="Error analysis by type">
        <thead>
          <tr>
            <th scope="col">Error Type</th>
            <th scope="col">Count</th>
            <th scope="col">%</th>
            <th scope="col">What Happened</th>
            <th scope="col">Why It Matters</th>
            <th scope="col">How Detected</th>
            <th scope="col">Prevention</th>
            <th scope="col">Follow-Up</th>
          </tr>
        </thead>
        <tbody>
          ${ea.by_type.map(r => `
          <tr>
            <td><span class="chip ${esc(r.type)}">${esc(r.type)}</span></td>
            <td><strong>${r.count}</strong></td>
            <td>${r.pct}%</td>
            <td>${esc(r.what_happened)}</td>
            <td>${esc(r.why_matters)}</td>
            <td>${esc(r.how_detected)}</td>
            <td>${esc(r.prevention)}</td>
            <td>${esc(r.followup)}</td>
          </tr>`).join('')}
        </tbody>
      </table>

      <h3 class="section-title" style="font-size:18px;margin-top:24px">⚠ Edge Cases Demonstrated</h3>
      ${renderEdgeCases()}
    </div>
  `;
}

function renderEdgeCases() {
  const cases = [
    {
      id: 'CASE 1 — MISSING EVENT',
      icon: '❌',
      scenario: 'missing_cleaning',
      description: 'Clinical readiness exists but cleaning completion is not recorded.',
      expected: 'MISSING status · Bed blocked from SAFE_AVAILABLE · Follow-up action created',
      actual: State.admissions.filter(v => v.scenario === 'missing_cleaning').length,
    },
    {
      id: 'CASE 2 — STALE DATA',
      icon: '⏰',
      scenario: 'stale_data',
      description: 'Cleaning record has not been updated in over 4 hours.',
      expected: 'STALE label with timestamp · Warning shown · Not accepted as fresh',
      actual: State.admissions.filter(v => v.scenario === 'stale_data').length,
    },
    {
      id: 'CASE 3 — CONFLICTING EVENTS',
      icon: '⚡',
      scenario: 'conflicting',
      description: 'Bed state says CLEANING but cleaning record says COMPLETED.',
      expected: 'CONFLICTING status · Safe availability blocked · Resolution action created',
      actual: State.admissions.filter(v => v.scenario === 'conflicting').length,
    },
    {
      id: 'CASE 4 — DUPLICATE EVENTS',
      icon: '⊙',
      scenario: 'duplicate_events',
      description: 'Same milestone or cleaning event recorded more than once.',
      expected: 'Duplicate flagged · Excluded from calculations',
      actual: State.admissions.filter(v => v.scenario === 'duplicate_events').length,
    },
    {
      id: 'CASE 5 — INVALID TIMESTAMP',
      icon: '🚫',
      scenario: 'invalid_timestamp',
      description: 'Cleaning completion timestamp is before the start timestamp.',
      expected: 'INVALID status · Record not used in metric calculations',
      actual: State.admissions.filter(v => v.scenario === 'invalid_timestamp').length,
    },
    {
      id: 'CASE 6 — INVALID SEQUENCE',
      icon: '🔀',
      scenario: 'invalid_sequence',
      description: 'Bed marked SAFE_AVAILABLE before cleaning was completed.',
      expected: 'INVALID_SEQUENCE flag · Bed not accepted as safely available',
      actual: State.admissions.filter(v => v.scenario === 'invalid_sequence').length,
    },
    {
      id: 'CASE 7 — ESCALATED OVERDUE',
      icon: '🔴',
      scenario: 'escalated_overdue',
      description: 'High-priority action is overdue — transfer delayed > 4 hours.',
      expected: 'ESCALATED badge · Remains visible until resolved',
      actual: State.admissions.filter(v => v.scenario === 'escalated_overdue').length,
    },
    {
      id: 'CASE 8 — BED REVERTED',
      icon: '↩',
      scenario: 'bed_revert',
      description: 'Bed was SAFE_AVAILABLE then reverted to UNAVAILABLE.',
      expected: 'Latest state shown · Previous safe availability not counted',
      actual: State.admissions.filter(v => v.scenario === 'bed_revert').length,
    },
  ];

  return cases.map(c => `
    <div style="background:#fff;border-radius:8px;padding:16px;margin-bottom:12px;box-shadow:0 1px 4px rgba(0,0,0,.08);border-left:5px solid #e2e8f0">
      <div style="font-size:16px;font-weight:800;margin-bottom:8px">${c.icon} ${esc(c.id)}</div>
      <div style="margin-bottom:6px"><strong>Scenario:</strong> ${esc(c.description)}</div>
      <div style="margin-bottom:6px"><strong>Expected:</strong> ${esc(c.expected)}</div>
      <div style="margin-bottom:6px"><strong>Records in dataset:</strong> <span style="font-weight:700;color:#1a3a5c">${c.actual}</span></div>
      ${c.actual > 0
        ? `<button class="btn btn-outline btn-sm" onclick="filterByScenario('${esc(c.scenario)}')">
             View these cases →
           </button>` : ''}
    </div>
  `).join('');
}

function filterByScenario(scenario) {
  // Navigate to board and filter
  State.filters.search = scenario;
  navigate('board');
}

// ══════════════════════════════════════════════════════════════════════════
// STAKEHOLDER VALIDATION
// ══════════════════════════════════════════════════════════════════════════
function renderStakeholder(container) {
  const roles = [
    { name: 'Bed Coordinator',   icon: '🗂️' },
    { name: 'Nurse',             icon: '👩‍⚕️' },
    { name: 'Doctor',            icon: '🩺' },
    { name: 'Housekeeping',      icon: '🧹' },
    { name: 'Transfer Coordinator', icon: '🚑' },
    { name: 'Administrator',     icon: '📊' },
  ];
  const questions = [
    'Can they identify delayed beds?',
    'Can they understand discharge readiness?',
    'Can they understand missing/stale information?',
    'Can they identify the owner?',
    'Can they understand the next action?',
    'Can users with limited digital literacy use the dashboard?',
  ];
  // Synthetic validation answers
  const answers = {
    'Bed Coordinator': ['YES','YES','YES','YES','YES','YES'],
    'Nurse':           ['YES','YES','YES','YES','YES','YES'],
    'Doctor':          ['YES','YES','PARTIAL','YES','YES','YES'],
    'Housekeeping':    ['YES','PARTIAL','YES','YES','YES','YES'],
    'Transfer Coordinator':['YES','YES','YES','YES','YES','YES'],
    'Administrator':   ['YES','YES','YES','YES','YES','YES'],
  };

  container.innerHTML = `
    <div class="main-container">
      <h2 class="section-title">👥 Synthetic Stakeholder Validation</h2>
      <div style="background:#eff6ff;border:2px solid #3b82f6;border-radius:8px;padding:14px;margin-bottom:20px">
        <strong>⚠ Note:</strong> This is a <em>synthetic stakeholder validation</em>.
        Actual users were not available. This validation simulates expected usability outcomes
        based on the implemented interface and accessibility features.
        It does <strong>not</strong> represent real user research.
      </div>

      ${roles.map(r => {
        const ans = answers[r.name] || [];
        return `
        <div class="stakeholder-card">
          <h3>${r.icon} ${esc(r.name)}</h3>
          <table class="sv-table">
            <thead><tr><th>Question</th><th>Result</th></tr></thead>
            <tbody>
              ${questions.map((q, i) => {
                const a = ans[i] || 'PARTIAL';
                return `<tr>
                  <td>${esc(q)}</td>
                  <td class="${a === 'YES' ? 'sv-pass' : a === 'NO' ? 'sv-fail' : ''}">${
                    a === 'YES' ? '✅ Yes' : a === 'NO' ? '❌ No' : '⚠ Partial'}</td>
                </tr>`;
              }).join('')}
            </tbody>
          </table>
        </div>`;
      }).join('')}
    </div>
  `;
}

// ══════════════════════════════════════════════════════════════════════════
// DETAIL MODAL
// ══════════════════════════════════════════════════════════════════════════
async function openDetail(admId) {
  let detail;
  try {
    detail = await apiFetch(`/api/admission/${admId}`);
  } catch (e) {
    alert('Could not load detail: ' + e.message);
    return;
  }

  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.setAttribute('role', 'dialog');
  overlay.setAttribute('aria-modal', 'true');
  overlay.setAttribute('aria-label', `Admission detail: ${detail.bed_id}`);

  const issues = detail.issues || [];
  const delay = detail.delay || {};
  const timeline = detail.timeline || [];

  overlay.innerHTML = `
    <div class="modal-box">
      <button class="modal-close" onclick="this.closest('.modal-overlay').remove()"
              aria-label="Close detail panel">✕ Close</button>
      <div class="modal-title">🛏 ${esc(detail.bed_id)} — ${esc(stageLabel(detail.stage))}</div>
      <div class="modal-subtitle">
        ${esc(detail.facility_id)} · ${esc(detail.ward)} · Patient ${esc(detail.patient_id)}
        · Acuity: <strong>${esc(detail.acuity)}</strong>
        · Transfer required: <strong>${detail.transfer_required ? 'Yes' : 'No'}</strong>
      </div>

      <!-- Issue chips -->
      ${issues.length
        ? `<div class="issue-chips" aria-label="Data quality issues found" style="margin-bottom:16px">
             ${issues.map(i => `<span class="chip ${esc(i.code)}" title="${esc(i.message)}">${esc(i.code)}: ${esc(i.message)}</span>`).join('')}
           </div>`
        : '<div style="color:#166534;font-weight:700;margin-bottom:16px">✅ No data quality issues detected</div>'
      }

      <!-- Metric -->
      <div style="background:#f0fdf4;border:2px solid #22c55e;border-radius:8px;padding:14px;margin-bottom:20px">
        <strong>⏱ Turnover Delay:</strong>
        ${delay.status === 'MEASURED'
          ? `<span style="font-size:18px;font-weight:800;color:#166534">${fmtMinutes(delay.delay_minutes)}</span>
             <span style="font-size:13px;color:#475569"> (readiness → safe available)</span>`
          : `<span style="color:#b91c1c;font-weight:700">${esc(delay.status)}: ${esc(delay.reason)}</span>`
        }
      </div>

      <!-- Freshness -->
      <div class="freshness-tag ${esc(detail.freshness_status)}" style="margin-bottom:16px;font-size:14px">
        ${esc(detail.freshness_text)}
      </div>

      <!-- Actions for this admission -->
      ${(detail.actions || []).length > 0 ? `
        <h4 style="font-size:15px;font-weight:700;margin-bottom:10px">📋 Follow-Up Actions</h4>
        ${detail.actions.map(a => `
          <div style="background:#fff7ed;border-left:4px solid #f59e0b;border-radius:6px;padding:12px;margin-bottom:8px;font-size:14px">
            ${priorityIcon(a.priority)} <strong>${esc(a.issue)}</strong><br>
            Owner: ${esc(a.owner || '—')} · Due: ${fmtTs(a.due_datetime)} · Status: <strong>${esc(a.status)}</strong>
            ${a.escalated ? '<span class="chip ESCALATED" style="margin-left:8px">🔴 ESCALATED</span>' : ''}
            <div style="margin-top:8px">
              <button class="btn btn-sm btn-success" onclick="updateAction('${esc(a.action_id)}','RESOLVED');this.closest('.modal-overlay').remove()">✅ Resolve</button>
              <button class="btn btn-sm btn-danger"  onclick="updateAction('${esc(a.action_id)}','ESCALATED');this.closest('.modal-overlay').remove()">🔴 Escalate</button>
            </div>
          </div>
        `).join('')}
      ` : ''}

      <!-- Evidence Timeline -->
      <h4 style="font-size:16px;font-weight:700;margin:16px 0 12px">📅 Evidence Timeline</h4>
      <div class="timeline" role="list" aria-label="Evidence timeline">
        ${timeline.map(e => `
          <div class="tl-event ${esc(e.quality)}" role="listitem">
            <div class="tl-type">
              ${esc(e.event_type)}
              ${qualityBadge(e.quality)}
            </div>
            <div class="tl-ts">🕐 ${fmtTs(e.timestamp)}</div>
            <div class="tl-detail">
              ${esc(e.detail || '')}
              ${e.status ? `<span style="font-size:12px;color:#475569"> · Status: ${esc(e.status)}</span>` : ''}
              ${e.source !== '—' ? `<span style="font-size:12px;color:#475569"> · Source: ${esc(e.source)}</span>` : ''}
            </div>
          </div>
        `).join('')}
      </div>
    </div>
  `;

  document.body.appendChild(overlay);
  overlay.addEventListener('click', e => {
    if (e.target === overlay) overlay.remove();
  });
  overlay.addEventListener('keydown', e => {
    if (e.key === 'Escape') overlay.remove();
  });
  // Focus close button
  overlay.querySelector('.modal-close').focus();
}

// ══════════════════════════════════════════════════════════════════════════
// FILTER BAR
// ══════════════════════════════════════════════════════════════════════════
function populateFilterDropdowns() {
  const facEl = document.getElementById('filter-facility');
  const wardEl = document.getElementById('filter-ward');
  const stageEl = document.getElementById('filter-stage');
  if (facEl) {
    facEl.innerHTML = '<option value="">All Facilities</option>'
      + State.facilities.map(f => `<option value="${esc(f)}">${esc(f)}</option>`).join('');
  }
  if (wardEl) {
    wardEl.innerHTML = '<option value="">All Wards</option>'
      + State.wards.map(w => `<option value="${esc(w)}">${esc(w)}</option>`).join('');
  }
  if (stageEl) {
    stageEl.innerHTML = '<option value="">All Stages</option>'
      + State.stages.map(s => `<option value="${esc(s)}">${esc(s)}</option>`).join('');
  }
}

function renderFilterBar() {
  return `
  <div class="filter-bar" role="search" aria-label="Filters">
    <label for="filter-search">🔍</label>
    <input type="text" id="filter-search" placeholder="Search patient, bed, facility..."
           value="${esc(State.filters.search)}" aria-label="Search"
           style="min-width:200px">
    <label for="filter-facility">Facility</label>
    <select id="filter-facility" aria-label="Filter by facility">
      <option value="">All Facilities</option>
      ${State.facilities.map(f => `<option value="${esc(f)}" ${State.filters.facility===f?'selected':''}>${esc(f)}</option>`).join('')}
    </select>
    <label for="filter-ward">Ward</label>
    <select id="filter-ward" aria-label="Filter by ward">
      <option value="">All Wards</option>
      ${State.wards.map(w => `<option value="${esc(w)}" ${State.filters.ward===w?'selected':''}>${esc(w)}</option>`).join('')}
    </select>
    <label for="filter-stage">Stage</label>
    <select id="filter-stage" aria-label="Filter by stage">
      <option value="">All Stages</option>
      ${State.stages.map(s => `<option value="${esc(s)}" ${State.filters.stage===s?'selected':''}>${esc(s)}</option>`).join('')}
    </select>
    <button class="filter-toggle ${State.filters.delayed ? 'active' : ''}" id="filter-delayed"
            aria-pressed="${State.filters.delayed}" aria-label="Show delayed only">⏰ Delayed</button>
    <button class="filter-toggle ${State.filters.stale ? 'active' : ''}" id="filter-stale"
            aria-pressed="${State.filters.stale}" aria-label="Show stale data only">⌛ Stale</button>
    <button class="filter-toggle ${State.filters.missing ? 'active' : ''}" id="filter-missing"
            aria-pressed="${State.filters.missing}" aria-label="Show missing data only">❌ Missing</button>
    <button class="filter-toggle ${State.filters.conflicting ? 'active' : ''}" id="filter-conflicting"
            aria-pressed="${State.filters.conflicting}" aria-label="Show conflicting data only">⚡ Conflicting</button>
    <button class="btn btn-outline btn-sm" id="filter-clear" aria-label="Clear all filters">✕ Clear</button>
  </div>`;
}

function attachFilterListeners() {
  const debounce = (fn, ms) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };
  const search = document.getElementById('filter-search');
  const facility = document.getElementById('filter-facility');
  const ward = document.getElementById('filter-ward');
  const stage = document.getElementById('filter-stage');
  const delayed = document.getElementById('filter-delayed');
  const stale = document.getElementById('filter-stale');
  const missing = document.getElementById('filter-missing');
  const conflicting = document.getElementById('filter-conflicting');
  const clear = document.getElementById('filter-clear');

  const applyFilters = debounce(async () => {
    if (search) State.filters.search = search.value;
    if (facility) State.filters.facility = facility.value;
    if (ward) State.filters.ward = ward.value;
    if (stage) State.filters.stage = stage.value;
    await loadAdmissions();
    const grid = document.getElementById('admission-grid');
    const kanban = document.querySelector('.kanban-wrapper');
    if (grid) grid.innerHTML = renderAdmissionCards(State.admissions);
    if (kanban) {
      // Re-render board
      renderBoard(document.getElementById('main-content'));
    }
  }, 300);

  if (search) search.addEventListener('input', applyFilters);
  if (facility) facility.addEventListener('change', applyFilters);
  if (ward) ward.addEventListener('change', applyFilters);
  if (stage) stage.addEventListener('change', applyFilters);

  [delayed, stale, missing, conflicting].forEach(btn => {
    if (!btn) return;
    btn.addEventListener('click', () => {
      const key = btn.id.replace('filter-', '');
      State.filters[key] = !State.filters[key];
      btn.classList.toggle('active', State.filters[key]);
      btn.setAttribute('aria-pressed', State.filters[key]);
      applyFilters();
    });
  });

  if (clear) {
    clear.addEventListener('click', () => {
      State.filters = { facility:'', ward:'', stage:'', search:'', delayed:false, stale:false, missing:false, conflicting:false };
      applyFilters();
    });
  }
}

// ══════════════════════════════════════════════════════════════════════════
// INIT
// ══════════════════════════════════════════════════════════════════════════
async function init() {
  // Nav
  document.querySelectorAll('.nav-links button').forEach(btn => {
    btn.addEventListener('click', () => navigate(btn.dataset.view));
  });

  // Role selector
  const roleSelect = document.getElementById('role-select');
  if (roleSelect) {
    roleSelect.addEventListener('change', () => setRole(roleSelect.value));
  }

  await loadFacilities();
  await loadDashboard();
  navigate('dashboard');
}

document.addEventListener('DOMContentLoaded', init);
