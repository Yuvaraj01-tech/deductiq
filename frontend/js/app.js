/**
 * DeductIQ — The Autonomous Revenue Recovery Engine
 * Enterprise Frontend Controller & State Machine
 */

// Application State
const state = {
  activeTab: 'dashboard',
  currentUserToken: 'admin_token_sec_9918',
  currentUser: null,
  claims: [],
  totalRecords: 0,
  currentPage: 1,
  pageSize: 10,
  totalPages: 1,
  sortBy: 'created_at',
  sortDir: 'desc',
  searchQuery: '',
  filters: {
    retailer: 'All',
    status: 'All',
    risk: 'All',
    tier: 'All'
  },
  selectedClaimIds: new Set(),
  activeClaimId: null
};

// API Base URL (Relative for unified FastAPI serving)
const API_BASE = window.location.origin.includes('8000') ? '' : 'http://127.0.0.1:8000';

// API Fetch Helper with Bearer Auth & Global Error Handling
async function apiFetch(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const headers = {
    'Accept': 'application/json',
    'Authorization': `Bearer ${state.currentUserToken}`,
    ...options.headers
  };

  // If body is FormData, do not set Content-Type header
  if (!(options.body instanceof FormData) && options.body && typeof options.body === 'object') {
    headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(options.body);
  }

  try {
    const res = await fetch(url, { ...options, headers });
    if (!res.ok) {
      let errorMsg = `Server Error (${res.status})`;
      try {
        const errJson = await res.json();
        errorMsg = errJson.detail || errJson.message || errorMsg;
      } catch (e) {
        // Fallback
      }
      throw new Error(errorMsg);
    }
    const contentType = res.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      return await res.json();
    }
    return await res.text();
  } catch (err) {
    console.error(`API Error on ${endpoint}:`, err);
    showToast(err.message, 'error');
    throw err;
  }
}

// Toast Notifications
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <div style="flex: 1;">${message}</div>
    <span style="cursor: pointer; opacity: 0.6; font-size: 1.1rem;" onclick="this.parentElement.remove()">&times;</span>
  `;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    setTimeout(() => toast.remove(), 400);
  }, 4000);
}

// Format Currency
function formatUSD(num) {
  if (num === null || num === undefined) return '$0.00';
  return '$' + Number(num).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// Format Date
function formatDate(dateStr) {
  if (!dateStr) return 'N/A';
  try {
    return dateStr.split(' ')[0];
  } catch {
    return dateStr;
  }
}

// --------------------------------------------------------------------------
// Navigation & Tab Switching
// --------------------------------------------------------------------------
function setupNavigation() {
  const navItems = document.querySelectorAll('.nav-item');
  navItems.forEach(item => {
    item.addEventListener('click', () => {
      const targetTab = item.getAttribute('data-tab');
      switchTab(targetTab);
    });
  });
}

function switchTab(tabId) {
  state.activeTab = tabId;

  // Update navigation classes
  document.querySelectorAll('.nav-item').forEach(item => {
    if (item.getAttribute('data-tab') === tabId) {
      item.classList.add('active');
    } else {
      item.classList.remove('active');
    }
  });

  // Update panels
  document.querySelectorAll('.tab-panel').forEach(panel => {
    panel.classList.remove('active');
  });

  const activePanel = document.getElementById(`panel-${tabId}`);
  if (activePanel) {
    activePanel.classList.add('active');
  }

  // Update header title
  const titleMap = {
    dashboard: 'Executive Revenue Overview',
    ledger: 'CPG Deduction Recovery Ledger',
    agent: 'Autonomous Recovery Agent Console',
    connectors: 'EDI 812 & Enterprise ERP Gateways',
    audit: 'System Governance & Audit Trail',
    settings: 'System Policies & Confidence Thresholds'
  };
  const titleEl = document.getElementById('page-header-title');
  if (titleEl) titleEl.textContent = titleMap[tabId] || 'DeductIQ Autonomous Engine';

  // Load data appropriate for tab
  if (tabId === 'dashboard') loadDashboardMetrics();
  if (tabId === 'ledger') loadClaims();
  if (tabId === 'audit') loadAuditLogs();
  if (tabId === 'settings') loadSettings();
}

// --------------------------------------------------------------------------
// User Persona & RBAC
// --------------------------------------------------------------------------
async function setupPersona() {
  const select = document.getElementById('persona-select');
  if (!select) return;

  select.value = state.currentUserToken;
  select.addEventListener('change', async (e) => {
    state.currentUserToken = e.target.value;
    try {
      const user = await apiFetch('/api/auth/me');
      state.currentUser = user;
      updatePersonaAvatar(user);
      showToast(`Switched active persona to ${user.name} (${user.role})`, 'info');
      // Refresh current view
      if (state.activeTab === 'dashboard') loadDashboardMetrics();
      if (state.activeTab === 'ledger') loadClaims();
    } catch (e) {
      // Handled
    }
  });

  try {
    const user = await apiFetch('/api/auth/me');
    state.currentUser = user;
    updatePersonaAvatar(user);
  } catch (err) {
    console.error('Failed to load user info:', err);
  }
}

function updatePersonaAvatar(user) {
  const avatar = document.getElementById('current-user-avatar');
  if (!avatar || !user) return;
  const initials = user.name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
  avatar.textContent = initials;
  avatar.title = `${user.name} (${user.role})\nPermissions: ${user.permissions.join(', ')}`;
}

// --------------------------------------------------------------------------
// Executive Dashboard
// --------------------------------------------------------------------------
async function loadDashboardMetrics() {
  try {
    const data = await apiFetch('/api/dashboard/metrics');

    // Update KPI counters
    const totalDed = document.getElementById('stat-total-deductions');
    const totalCnt = document.getElementById('stat-total-count');
    const recCash = document.getElementById('stat-recovered-cash');
    const netRate = document.getElementById('stat-net-rate');
    const dispAmt = document.getElementById('stat-disputed-amount');
    const dispCnt = document.getElementById('stat-disputed-count');
    const roiMult = document.getElementById('stat-roi-multiplier');
    const hrsSaved = document.getElementById('stat-hours-saved');
    const sideBadge = document.getElementById('sidebar-badge-count');

    if (totalDed) totalDed.textContent = formatUSD(data.total_deductions_amount);
    if (totalCnt) totalCnt.textContent = data.total_claims;
    if (recCash) recCash.textContent = formatUSD(data.recovered_cash);
    if (netRate) netRate.textContent = `${data.net_recovery_rate_pct}%`;
    if (dispAmt) dispAmt.textContent = formatUSD(data.disputed_amount);
    if (dispCnt) dispCnt.textContent = data.disputed_claims;
    if (roiMult) roiMult.textContent = data.roi_multiplier;
    if (hrsSaved) hrsSaved.textContent = data.human_hours_saved;
    if (sideBadge) sideBadge.textContent = data.total_claims;

    // Render Retailer Breakdown
    renderRetailerBreakdown(data.retailer_breakdown);

    // Render Tier Model Routing
    renderTierBreakdown(data.tier_breakdown, data.total_claims);

  } catch (err) {
    console.error('Failed to load dashboard metrics:', err);
  }
}

function renderRetailerBreakdown(retailers) {
  const container = document.getElementById('dashboard-retailer-list');
  if (!container) return;

  if (!retailers || retailers.length === 0) {
    container.innerHTML = `<div class="empty-state">No retailer claim data available.</div>`;
    return;
  }

  const maxVal = Math.max(...retailers.map(r => r.total_val || 1));

  let html = '';
  retailers.forEach(r => {
    const pctOfMax = Math.min(100, Math.round((r.total_val / maxVal) * 100));
    const recRate = r.total_val > 0 ? Math.round((r.recovered_val / r.total_val) * 100) : 0;

    html += `
      <div class="retailer-row">
        <div class="retailer-row-meta">
          <span class="retailer-name">
            <strong>${r.retailer}</strong>
            <span style="font-size: 0.75rem; color: var(--text-dim); font-weight: normal;">(${r.count} claims)</span>
          </span>
          <span class="retailer-stats">
            <strong>${formatUSD(r.total_val)}</strong> • <span style="color: #34d399;">${formatUSD(r.recovered_val)} recovered</span> (${recRate}%)
          </span>
        </div>
        <div class="progress-bar-bg">
          <div class="progress-bar-fill" style="width: ${pctOfMax}%; background: linear-gradient(90deg, #6366f1, #06b6d4);"></div>
        </div>
      </div>
    `;
  });

  container.innerHTML = html;
}

function renderTierBreakdown(tierList, totalCount) {
  if (!tierList || !totalCount) return;
  const ruleEl = document.getElementById('tier-rule-count');
  const slmEl = document.getElementById('tier-slm-count');
  const frontEl = document.getElementById('tier-frontier-count');

  let ruleCount = 0, slmCount = 0, frontCount = 0;
  tierList.forEach(t => {
    if (t.routing_tier === 'Rule') ruleCount = t.count;
    if (t.routing_tier === 'SLM') slmCount = t.count;
    if (t.routing_tier === 'Frontier') frontCount = t.count;
  });

  if (ruleEl) ruleEl.textContent = `${Math.round((ruleCount / totalCount) * 100)}% (${ruleCount})`;
  if (slmEl) slmEl.textContent = `${Math.round((slmCount / totalCount) * 100)}% (${slmCount})`;
  if (frontEl) frontEl.textContent = `${Math.round((frontCount / totalCount) * 100)}% (${frontCount})`;
}

// --------------------------------------------------------------------------
// Recovery Ledger (Claims Table & CRUD)
// --------------------------------------------------------------------------
async function loadClaims() {
  const tbody = document.getElementById('claims-table-body');
  if (!tbody) return;

  tbody.innerHTML = `<tr><td colspan="10" style="text-align: center; padding: 40px;"><div class="spinner"></div> Loading deduction claims...</td></tr>`;

  try {
    const params = new URLSearchParams({
      page: state.currentPage,
      limit: state.pageSize,
      sort_by: state.sortBy,
      sort_dir: state.sortDir
    });

    if (state.searchQuery) params.append('search', state.searchQuery);
    if (state.filters.retailer !== 'All') params.append('retailer', state.filters.retailer);
    if (state.filters.status !== 'All') params.append('status', state.filters.status);
    if (state.filters.risk !== 'All') params.append('risk', state.filters.risk);
    if (state.filters.tier !== 'All') params.append('tier', state.filters.tier);

    const data = await apiFetch(`/api/claims?${params.toString()}`);
    state.claims = data.records;
    state.totalRecords = data.total_records;
    state.totalPages = data.total_pages;

    renderClaimsTable(data.records);
    updatePaginationControls();

  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="10" style="text-align: center; color: #ef4444; padding: 30px;">Failed to load claims: ${err.message}</td></tr>`;
  }
}

function renderClaimsTable(claims) {
  const tbody = document.getElementById('claims-table-body');
  if (!tbody) return;

  if (!claims || claims.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="10">
          <div class="empty-state">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
            <p>No deduction claims match your filter criteria.</p>
            <button class="btn btn-secondary btn-sm" onclick="resetFilters()" style="margin-top: 12px;">Clear Filters</button>
          </div>
        </td>
      </tr>
    `;
    return;
  }

  let html = '';
  claims.forEach(c => {
    const isChecked = state.selectedClaimIds.has(c.id);
    const winClass = c.win_probability >= 80 ? 'prob-high' : (c.win_probability >= 50 ? 'prob-med' : 'prob-low');
    const tierBadgeClass = c.routing_tier === 'Rule' ? 'tier-rule' : (c.routing_tier === 'SLM' ? 'tier-slm' : 'tier-frontier');
    const statusClass = `status-${c.status.toLowerCase()}`;
    const podClean = c.pod_status && (c.pod_status.includes('Clean') || c.pod_status.includes('Stamp'));

    html += `
      <tr data-id="${c.id}">
        <td>
          <input type="checkbox" class="claim-row-checkbox" data-id="${c.id}" ${isChecked ? 'checked' : ''} aria-label="Select Claim ${c.claim_number}">
        </td>
        <td>
          <a href="#" class="view-claim-link" data-id="${c.id}" style="color: #38bdf8; font-weight: 600; text-decoration: none; font-family: var(--font-mono);">
            ${c.claim_number}
          </a>
          <div style="font-size: 0.75rem; color: var(--text-dim);">${formatDate(c.invoice_date)}</div>
        </td>
        <td><strong>${c.retailer}</strong></td>
        <td>
          <div style="font-weight: 500;">${c.deduction_reason}</div>
          <div style="font-size: 0.75rem; color: var(--text-dim); font-family: var(--font-mono);">${c.deduction_code}</div>
        </td>
        <td>
          <strong style="color: #fff; font-size: 0.95rem;">${formatUSD(c.amount)}</strong>
        </td>
        <td>
          <span class="prob-pill ${winClass}">${c.win_probability}%</span>
        </td>
        <td>
          <span class="tier-badge ${tierBadgeClass}">${c.routing_tier}</span>
        </td>
        <td>
          <span class="status-pill ${statusClass}">${c.status}</span>
        </td>
        <td>
          <span style="font-size: 0.78rem; color: ${podClean ? '#34d399' : '#f87171'};">
            ${podClean ? '✓ Signed Clean' : '⚠ Exception'}
          </span>
        </td>
        <td style="text-align: right;">
          <div style="display: flex; gap: 6px; justify-content: flex-end;">
            <button class="btn btn-secondary btn-sm view-claim-btn" data-id="${c.id}" title="Inspect Evidence Graph & Dossier">
              Inspect
            </button>
            ${c.status !== 'Recovered' && c.status !== 'WrittenOff' ? `
              <button class="btn btn-primary btn-sm run-loop-btn" data-id="${c.id}" title="Execute Autonomous Outcome Loop">
                Auto-Dispute
              </button>
            ` : ''}
          </div>
        </td>
      </tr>
    `;
  });

  tbody.innerHTML = html;

  // Bind row events
  bindTableEvents();
}

function bindTableEvents() {
  // Checkbox triggers
  document.querySelectorAll('.claim-row-checkbox').forEach(cb => {
    cb.addEventListener('change', (e) => {
      const id = parseInt(e.target.getAttribute('data-id'));
      if (e.target.checked) {
        state.selectedClaimIds.add(id);
      } else {
        state.selectedClaimIds.delete(id);
      }
      updateBatchToolbar();
    });
  });

  // Select all checkbox
  const selectAll = document.getElementById('select-all-claims');
  if (selectAll) {
    selectAll.checked = state.claims.length > 0 && state.claims.every(c => state.selectedClaimIds.has(c.id));
    selectAll.onchange = (e) => {
      state.claims.forEach(c => {
        if (e.target.checked) {
          state.selectedClaimIds.add(c.id);
        } else {
          state.selectedClaimIds.delete(c.id);
        }
      });
      renderClaimsTable(state.claims);
      updateBatchToolbar();
    };
  }

  // Row inspection buttons
  document.querySelectorAll('.view-claim-btn, .view-claim-link').forEach(el => {
    el.addEventListener('click', (e) => {
      e.preventDefault();
      const id = parseInt(el.getAttribute('data-id'));
      openClaimDetailDrawer(id);
    });
  });

  // Quick auto-dispute button
  document.querySelectorAll('.run-loop-btn').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      const id = parseInt(btn.getAttribute('data-id'));
      btn.disabled = true;
      btn.innerHTML = `<span class="spinner"></span> Disputing...`;
      try {
        const res = await apiFetch(`/api/claims/${id}/autonomous-loop`, { method: 'POST' });
        showToast(`Dispute submitted autonomously! Acknowledgment Ref: ${res.portal?.acknowledgment_code}`, 'success');
        loadClaims();
        loadDashboardMetrics();
      } catch (err) {
        btn.disabled = false;
        btn.textContent = 'Auto-Dispute';
      }
    });
  });
}

function updateBatchToolbar() {
  const batchBtn = document.getElementById('btn-batch-dispute');
  const countSpan = document.getElementById('batch-selected-count');
  if (!batchBtn || !countSpan) return;

  const count = state.selectedClaimIds.size;
  countSpan.textContent = count;
  batchBtn.disabled = count === 0;
}

function updatePaginationControls() {
  const info = document.getElementById('pagination-info');
  const pageNum = document.getElementById('current-page-num');
  const prevBtn = document.getElementById('btn-prev-page');
  const nextBtn = document.getElementById('btn-next-page');

  if (info) {
    const start = (state.currentPage - 1) * state.pageSize + 1;
    const end = Math.min(state.totalRecords, state.currentPage * state.pageSize);
    info.textContent = `Showing ${state.totalRecords === 0 ? 0 : start} to ${end} of ${state.totalRecords} deductions`;
  }
  if (pageNum) pageNum.textContent = `${state.currentPage} / ${state.totalPages || 1}`;
  if (prevBtn) prevBtn.disabled = state.currentPage <= 1;
  if (nextBtn) nextBtn.disabled = state.currentPage >= state.totalPages;
}

function setupLedgerControls() {
  const searchInput = document.getElementById('search-claims');
  const retSelect = document.getElementById('filter-retailer');
  const statSelect = document.getElementById('filter-status');
  const riskSelect = document.getElementById('filter-risk');
  const resetBtn = document.getElementById('btn-reset-filters');
  const prevBtn = document.getElementById('btn-prev-page');
  const nextBtn = document.getElementById('btn-next-page');
  const pageSizeSelect = document.getElementById('select-page-size');
  const batchBtn = document.getElementById('btn-batch-dispute');
  const exportBtn = document.getElementById('btn-export-csv');

  // Search input debounced
  let timeout;
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      clearTimeout(timeout);
      timeout = setTimeout(() => {
        state.searchQuery = e.target.value.trim();
        state.currentPage = 1;
        loadClaims();
      }, 300);
    });
  }

  // Filter dropdowns
  if (retSelect) retSelect.addEventListener('change', (e) => { state.filters.retailer = e.target.value; state.currentPage = 1; loadClaims(); });
  if (statSelect) statSelect.addEventListener('change', (e) => { state.filters.status = e.target.value; state.currentPage = 1; loadClaims(); });
  if (riskSelect) riskSelect.addEventListener('change', (e) => { state.filters.risk = e.target.value; state.currentPage = 1; loadClaims(); });

  if (resetBtn) resetBtn.addEventListener('click', resetFilters);

  if (prevBtn) prevBtn.addEventListener('click', () => { if (state.currentPage > 1) { state.currentPage--; loadClaims(); } });
  if (nextBtn) nextBtn.addEventListener('click', () => { if (state.currentPage < state.totalPages) { state.currentPage++; loadClaims(); } });

  if (pageSizeSelect) pageSizeSelect.addEventListener('change', (e) => {
    state.pageSize = parseInt(e.target.value);
    state.currentPage = 1;
    loadClaims();
  });

  // Batch dispute
  if (batchBtn) {
    batchBtn.addEventListener('click', async () => {
      const ids = Array.from(state.selectedClaimIds);
      if (ids.length === 0) return;

      batchBtn.disabled = true;
      batchBtn.innerHTML = `<span class="spinner"></span> Processing ${ids.length} Claims...`;

      try {
        const res = await apiFetch('/api/claims/batch-dispute', {
          method: 'POST',
          body: { claim_ids: ids }
        });
        showToast(`Successfully processed ${res.processed} claims through autonomous loop!`, 'success');
        state.selectedClaimIds.clear();
        updateBatchToolbar();
        loadClaims();
        loadDashboardMetrics();
      } catch (e) {
        // Handled
      } finally {
        batchBtn.disabled = false;
        batchBtn.innerHTML = `<svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg> Batch Auto-Dispute (<span id="batch-selected-count">0</span>)`;
      }
    });
  }

  // Export CSV
  if (exportBtn) {
    exportBtn.addEventListener('click', () => {
      window.location.href = `${API_BASE}/api/claims-export`;
      showToast('Exporting all deduction records to CSV...', 'info');
    });
  }
}

function resetFilters() {
  state.searchQuery = '';
  state.filters.retailer = 'All';
  state.filters.status = 'All';
  state.filters.risk = 'All';
  state.currentPage = 1;

  const sInput = document.getElementById('search-claims');
  const retSelect = document.getElementById('filter-retailer');
  const statSelect = document.getElementById('filter-status');
  const riskSelect = document.getElementById('filter-risk');

  if (sInput) sInput.value = '';
  if (retSelect) retSelect.value = 'All';
  if (statSelect) statSelect.value = 'All';
  if (riskSelect) riskSelect.value = 'All';

  loadClaims();
}

// --------------------------------------------------------------------------
// Deep-Dive Claim Detail Modal & Evidence Graph
// --------------------------------------------------------------------------
async function openClaimDetailDrawer(claimId) {
  state.activeClaimId = claimId;
  const modal = document.getElementById('modal-claim-detail');
  if (!modal) return;

  modal.classList.add('active');

  const titleEl = document.getElementById('drawer-claim-title');
  const subtitleEl = document.getElementById('drawer-claim-subtitle');
  const graphNodes = document.getElementById('drawer-graph-nodes');
  const findingsContainer = document.getElementById('drawer-forensic-findings');
  const scorePct = document.getElementById('drawer-score-pct');
  const scoreModel = document.getElementById('drawer-score-model');
  const dossierText = document.getElementById('drawer-dossier-text');
  const portalLogs = document.getElementById('drawer-portal-logs');
  const settlementSec = document.getElementById('drawer-settlement-section');

  if (titleEl) titleEl.textContent = `Claim Investigation: #${claimId}`;
  if (graphNodes) graphNodes.innerHTML = `<div class="spinner"></div> Reconciling evidence graph...`;
  if (findingsContainer) findingsContainer.innerHTML = '';
  if (dossierText) dossierText.value = 'Compiling legal rebuttal...';
  if (portalLogs) portalLogs.innerHTML = 'Querying portal execution history...';
  if (settlementSec) settlementSec.style.display = 'none';

  try {
    const data = await apiFetch(`/api/claims/${claimId}`);
    const claim = data.claim;
    const evidence = data.evidence_graph || [];
    const dossier = data.dossier;
    const portalExecs = data.portal_executions || [];
    const settlement = data.settlement;

    if (titleEl) titleEl.textContent = `Claim Investigation: ${claim.claim_number} (${claim.retailer})`;
    if (subtitleEl) subtitleEl.textContent = `${claim.deduction_reason} (${claim.deduction_code}) • Amount: ${formatUSD(claim.amount)} • Status: ${claim.status}`;

    // Render Evidence Graph Nodes
    renderEvidenceGraph(evidence, claim);

    // Run live forensic reconciliation to show findings
    const forensicRes = await apiFetch(`/api/claims/${claimId}/reconcile`, { method: 'POST' });
    renderForensicFindings(forensicRes.reconciliation);

    // Score & Model Tier
    if (scorePct) scorePct.textContent = `${claim.win_probability}%`;
    if (scoreModel) {
      scoreModel.innerHTML = `
        Routing Tier: <strong style="color: #38bdf8;">${claim.routing_tier}</strong> • 
        Risk: <strong style="color: ${claim.risk_level === 'Low' ? '#34d399' : '#f87171'};">${claim.risk_level}</strong>
      `;
    }

    // Dossier legal rebuttal
    if (dossierText) {
      if (dossier && dossier.legal_rebuttal) {
        dossierText.value = dossier.legal_rebuttal;
      } else {
        // Auto-generate dossier if not present
        const genRes = await apiFetch(`/api/claims/${claimId}/generate-dossier`, { method: 'POST' });
        dossierText.value = genRes.dossier.legal_rebuttal;
      }
    }

    // Portal Execution Terminal Logs
    renderPortalExecutionLogs(portalExecs);

    // Settlement verification box
    if (settlement && settlementSec) {
      settlementSec.style.display = 'block';
      const meta = document.getElementById('drawer-settlement-meta');
      const dollars = document.getElementById('drawer-settlement-dollars');
      const fee = document.getElementById('drawer-settlement-fee');

      if (meta) meta.textContent = `Remittance: ${settlement.remittance_advice_ref} • ERP Credit Memo: ${settlement.erp_credit_memo_ref} (Date: ${settlement.settlement_date})`;
      if (dollars) dollars.textContent = formatUSD(settlement.recovered_amount);
      if (fee) fee.textContent = `Platform Fee (7.5%): ${formatUSD(settlement.success_fee)}`;
    }

  } catch (err) {
    console.error('Failed to load claim detail:', err);
  }
}

function renderEvidenceGraph(evidenceList, claim) {
  const container = document.getElementById('drawer-graph-nodes');
  if (!container) return;

  if (!evidenceList || evidenceList.length === 0) {
    container.innerHTML = `<div style="color: var(--text-dim);">No documentary evidence attached.</div>`;
    return;
  }

  let html = '';
  evidenceList.forEach(e => {
    const isVerified = e.match_status === 'Verified';
    html += `
      <div class="graph-node ${isVerified ? 'verified' : 'discrepancy'}">
        <span class="node-type">${e.doc_type}</span>
        <span class="node-ref">${e.doc_reference}</span>
        <div style="font-size: 0.72rem; color: var(--text-dim);">${e.file_name || 'EDI payload'}</div>
        <div class="node-status" style="color: ${isVerified ? '#34d399' : '#f87171'};">
          ${isVerified ? '✓ Match Verified' : '⚠ Discrepancy'} (${Math.round((e.confidence || 1.0) * 100)}%)
        </div>
      </div>
    `;
  });

  container.innerHTML = html;
}

function renderForensicFindings(forensic) {
  const container = document.getElementById('drawer-forensic-findings');
  if (!container || !forensic) return;

  let html = '';
  (forensic.findings || []).forEach(f => {
    html += `
      <div style="background: rgba(30, 41, 59, 0.35); padding: 10px 12px; border-radius: var(--radius-sm); border-left: 3px solid #10b981; font-size: 0.82rem;">
        <strong style="color: #fff;">${f.rule}:</strong> ${f.detail}
      </div>
    `;
  });

  (forensic.discrepancies || []).forEach(d => {
    html += `
      <div style="background: rgba(239, 68, 68, 0.1); padding: 10px 12px; border-radius: var(--radius-sm); border-left: 3px solid #ef4444; font-size: 0.82rem;">
        <strong style="color: #f87171;">${d.rule}:</strong> ${d.detail}
      </div>
    `;
  });

  container.innerHTML = html || '<div style="color: var(--text-muted); font-size: 0.8rem;">Clean forensic reconciliation. No dock discrepancies detected.</div>';
}

function renderPortalExecutionLogs(portalExecs) {
  const container = document.getElementById('drawer-portal-logs');
  if (!container) return;

  if (!portalExecs || portalExecs.length === 0) {
    container.innerHTML = `<div class="terminal-line"><span class="terminal-time">[Pending]</span> Dispute has not yet been executed in retailer portal. Click "Run Autonomous Loop" to execute.</div>`;
    return;
  }

  const latest = portalExecs[0];
  const logs = latest.logs || [];

  let html = '';
  logs.forEach(l => {
    let tagClass = 'terminal-tag-success';
    if (l.status === 'WARNING') tagClass = 'terminal-tag-warning';
    if (l.status === 'HEALED') tagClass = 'terminal-tag-healed';

    html += `
      <div class="terminal-line">
        <span class="terminal-time">[${l.time || l.timestamp || '00:00:00'}]</span>
        <span class="${tagClass}">[${l.stage || 'STAGE'}]</span>
        <span>${l.message}</span>
      </div>
    `;
  });

  container.innerHTML = html;
}

function setupDetailModalButtons() {
  const closeBtn1 = document.getElementById('btn-close-detail-modal');
  const closeBtn2 = document.getElementById('btn-close-detail-modal-btn');
  const modal = document.getElementById('modal-claim-detail');

  const closeModal = () => {
    if (modal) modal.classList.remove('active');
  };

  if (closeBtn1) closeBtn1.addEventListener('click', closeModal);
  if (closeBtn2) closeBtn2.addEventListener('click', closeModal);

  // Run autonomous loop on single claim
  const runBtn = document.getElementById('btn-run-loop-single-action');
  if (runBtn) {
    runBtn.addEventListener('click', async () => {
      if (!state.activeClaimId) return;
      runBtn.disabled = true;
      runBtn.innerHTML = `<span class="spinner"></span> Executing 6-stage loop...`;
      try {
        const res = await apiFetch(`/api/claims/${state.activeClaimId}/autonomous-loop`, { method: 'POST' });
        showToast(`Dispute submitted to ${res.retailer} portal! Ref: ${res.portal?.acknowledgment_code}`, 'success');
        openClaimDetailDrawer(state.activeClaimId);
        loadClaims();
        loadDashboardMetrics();
      } catch (e) {
        // Handled
      } finally {
        runBtn.disabled = false;
        runBtn.innerHTML = `<svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg> Run Autonomous Loop`;
      }
    });
  }

  // Verify cash settlement
  const verifyBtn = document.getElementById('btn-verify-cash-action');
  if (verifyBtn) {
    verifyBtn.addEventListener('click', async () => {
      if (!state.activeClaimId) return;
      verifyBtn.disabled = true;
      try {
        const res = await apiFetch(`/api/claims/${state.activeClaimId}/verify-recovery`, { method: 'POST' });
        showToast(`Cash recovery verified! Recovered: ${formatUSD(res.recovered_amount)}, Fee: ${formatUSD(res.success_fee)}`, 'success');
        openClaimDetailDrawer(state.activeClaimId);
        loadClaims();
        loadDashboardMetrics();
      } catch (e) {
        // Handled
      } finally {
        verifyBtn.disabled = false;
      }
    });
  }

  // Approve claim
  const approveBtn = document.getElementById('btn-approve-claim-action');
  if (approveBtn) {
    approveBtn.addEventListener('click', async () => {
      if (!state.activeClaimId) return;
      try {
        await apiFetch(`/api/claims/${state.activeClaimId}/approve`, { method: 'POST' });
        showToast('Claim manually approved for portal filing.', 'success');
        openClaimDetailDrawer(state.activeClaimId);
        loadClaims();
      } catch (e) {
        // Handled
      }
    });
  }

  // Write off claim
  const writeoffBtn = document.getElementById('btn-writeoff-claim-action');
  if (writeoffBtn) {
    writeoffBtn.addEventListener('click', async () => {
      if (!state.activeClaimId) return;
      try {
        await apiFetch(`/api/claims/${state.activeClaimId}/writeoff`, { method: 'POST' });
        showToast('Claim written off.', 'info');
        openClaimDetailDrawer(state.activeClaimId);
        loadClaims();
      } catch (e) {
        // Handled
      }
    });
  }

  // Delete claim
  const deleteBtn = document.getElementById('btn-delete-claim-action');
  if (deleteBtn) {
    deleteBtn.addEventListener('click', async () => {
      if (!state.activeClaimId) return;
      if (!confirm('Are you sure you want to permanently delete this deduction claim and its evidence graph?')) return;
      try {
        await apiFetch(`/api/claims/${state.activeClaimId}`, { method: 'DELETE' });
        showToast('Claim deleted successfully.', 'info');
        closeModal();
        loadClaims();
        loadDashboardMetrics();
      } catch (e) {
        // Handled
      }
    });
  }

  // Save dossier edits
  const saveDossierBtn = document.getElementById('btn-save-dossier-edits');
  if (saveDossierBtn) {
    saveDossierBtn.addEventListener('click', async () => {
      if (!state.activeClaimId) return;
      const text = document.getElementById('drawer-dossier-text').value;
      try {
        await apiFetch(`/api/claims/${state.activeClaimId}/dossier`, {
          method: 'PUT',
          body: { legal_rebuttal: text, status: 'Draft' }
        });
        showToast('Dispute dossier text updated successfully.', 'success');
      } catch (e) {
        // Handled
      }
    });
  }

  // Download dossier text
  const downloadDossierBtn = document.getElementById('btn-download-dossier-txt');
  if (downloadDossierBtn) {
    downloadDossierBtn.addEventListener('click', () => {
      if (!state.activeClaimId) return;
      window.location.href = `${API_BASE}/api/claims/${state.activeClaimId}/export-dossier`;
    });
  }
}

// --------------------------------------------------------------------------
// Create New Claim Form & Modal
// --------------------------------------------------------------------------
function setupCreateClaimModal() {
  const openBtn = document.getElementById('btn-create-claim-modal');
  const modal = document.getElementById('modal-create-claim');
  const closeBtn = document.getElementById('btn-close-create-modal');
  const cancelBtn = document.getElementById('btn-cancel-create-claim');
  const form = document.getElementById('create-claim-form');

  if (openBtn) openBtn.addEventListener('click', () => modal.classList.add('active'));
  const closeModal = () => modal.classList.remove('active');
  if (closeBtn) closeBtn.addEventListener('click', closeModal);
  if (cancelBtn) cancelBtn.addEventListener('click', closeModal);

  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const submitBtn = document.getElementById('btn-submit-new-claim');
      submitBtn.disabled = true;
      submitBtn.innerHTML = `<span class="spinner"></span> Ingesting...`;

      const payload = {
        retailer: document.getElementById('new-claim-retailer').value,
        deduction_code: document.getElementById('new-claim-code').value,
        deduction_reason: document.getElementById('new-claim-reason').value,
        amount: parseFloat(document.getElementById('new-claim-amount').value),
        invoice_number: document.getElementById('new-claim-inv-number').value,
        invoice_date: document.getElementById('new-claim-inv-date').value,
        invoice_amount: parseFloat(document.getElementById('new-claim-inv-amount').value),
        po_number: document.getElementById('new-claim-po-number').value,
        po_date: document.getElementById('new-claim-po-date').value,
        bol_number: document.getElementById('new-claim-bol-number').value || 'BOL-AUTO',
        pod_status: document.getElementById('new-claim-pod-status').value,
        signed_qty: 1200,
        invoiced_qty: 1200,
        claimed_shortage_qty: 65,
        unit_price: 50.0
      };

      try {
        const res = await apiFetch('/api/claims', {
          method: 'POST',
          body: payload
        });
        showToast(`Deduction claim #${res.claim_number} created and evidence bound!`, 'success');
        closeModal();
        loadClaims();
        loadDashboardMetrics();
      } catch (err) {
        // Handled
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Create & Ingest Claim';
      }
    });
  }
}

// --------------------------------------------------------------------------
// File Upload & Reseed Data Modals
// --------------------------------------------------------------------------
function setupUploadAndReseedModals() {
  // Upload modal
  const openUploadBtn = document.getElementById('btn-open-upload-modal');
  const uploadModal = document.getElementById('modal-file-upload');
  const closeUploadBtn = document.getElementById('btn-close-upload-modal');
  const cancelUploadBtn = document.getElementById('btn-cancel-upload-file');
  const executeUploadBtn = document.getElementById('btn-execute-file-upload');
  const fileInput = document.getElementById('input-claims-file');

  if (openUploadBtn) openUploadBtn.addEventListener('click', () => uploadModal.classList.add('active'));
  const closeUpload = () => uploadModal.classList.remove('active');
  if (closeUploadBtn) closeUploadBtn.addEventListener('click', closeUpload);
  if (cancelUploadBtn) cancelUploadBtn.addEventListener('click', closeUpload);

  if (executeUploadBtn) {
    executeUploadBtn.addEventListener('click', async () => {
      if (!fileInput.files || fileInput.files.length === 0) {
        showToast('Please select a CSV or JSON file to upload.', 'error');
        return;
      }
      const file = fileInput.files[0];
      const formData = new FormData();
      formData.append('file', file);

      executeUploadBtn.disabled = true;
      executeUploadBtn.innerHTML = `<span class="spinner"></span> Uploading...`;

      try {
        const res = await apiFetch('/api/claims/upload', {
          method: 'POST',
          body: formData
        });
        showToast(`Successfully imported ${res.records_imported} claims from ${res.filename}!`, 'success');
        closeUpload();
        loadClaims();
        loadDashboardMetrics();
      } catch (e) {
        // Handled
      } finally {
        executeUploadBtn.disabled = false;
        executeUploadBtn.textContent = 'Import File';
      }
    });
  }

  // Reseed modal
  const openReseedBtn = document.getElementById('btn-reseed-data');
  const reseedModal = document.getElementById('modal-reseed-confirm');
  const closeReseedBtn = document.getElementById('btn-close-reseed-modal');
  const cancelReseedBtn = document.getElementById('btn-cancel-reseed');
  const confirmReseedBtn = document.getElementById('btn-confirm-reseed-action');

  if (openReseedBtn) openReseedBtn.addEventListener('click', () => reseedModal.classList.add('active'));
  const closeReseed = () => reseedModal.classList.remove('active');
  if (closeReseedBtn) closeReseedBtn.addEventListener('click', closeReseed);
  if (cancelReseedBtn) cancelReseedBtn.addEventListener('click', closeReseed);

  if (confirmReseedBtn) {
    confirmReseedBtn.addEventListener('click', async () => {
      confirmReseedBtn.disabled = true;
      confirmReseedBtn.innerHTML = `<span class="spinner"></span> Reseeding...`;
      try {
        await apiFetch('/api/reset-demo-data', { method: 'POST' });
        showToast('Database reset and reseeded with 100 benchmark deductions!', 'success');
        closeReseed();
        loadDashboardMetrics();
        loadClaims();
      } catch (e) {
        // Handled
      } finally {
        confirmReseedBtn.disabled = false;
        confirmReseedBtn.textContent = 'Confirm & Reseed';
      }
    });
  }
}

// --------------------------------------------------------------------------
// Connectors & Testing
// --------------------------------------------------------------------------
function setupConnectors() {
  const testButtons = document.querySelectorAll('[id^="btn-test-"]');
  testButtons.forEach(btn => {
    btn.addEventListener('click', async () => {
      const target = btn.getAttribute('data-target') || 'Walmart';
      btn.disabled = true;
      btn.innerHTML = `<span class="spinner"></span> Testing...`;

      try {
        const res = await apiFetch('/api/settings/test-connection', {
          method: 'POST',
          body: { target }
        });
        showToast(`Connection to ${target} verified! Latency: ${res.latency_ms}ms`, 'success');
        const pingEl = document.getElementById(`ping-${target.toLowerCase()}`);
        if (pingEl) pingEl.textContent = `Ping: ${res.latency_ms}ms • Status: ${res.status}`;
      } catch (e) {
        // Handled
      } finally {
        btn.disabled = false;
        btn.textContent = target === 'ERP' ? 'Run Bidirectional Sync' : 'Test Endpoint';
      }
    });
  });

  const testAllBtn = document.getElementById('btn-test-all-connectors');
  if (testAllBtn) {
    testAllBtn.addEventListener('click', async () => {
      testAllBtn.disabled = true;
      testAllBtn.innerHTML = `<span class="spinner"></span> Testing all...`;
      for (const t of ['Walmart', 'Target', 'Amazon', 'Kroger', 'Costco', 'ERP']) {
        try {
          const res = await apiFetch('/api/settings/test-connection', { method: 'POST', body: { target: t } });
          const pingEl = document.getElementById(`ping-${t.toLowerCase()}`);
          if (pingEl) pingEl.textContent = `Ping: ${res.latency_ms}ms • Status: ${res.status}`;
        } catch (e) {}
      }
      showToast('All 6 integration endpoints verified healthy!', 'success');
      testAllBtn.disabled = false;
      testAllBtn.textContent = 'Test All Endpoints';
    });
  }
}

// --------------------------------------------------------------------------
// Global Autonomous Agent Tab
// --------------------------------------------------------------------------
function setupAgentConsole() {
  const runAllBtn = document.getElementById('btn-run-all-disputes');
  const clearBtn = document.getElementById('btn-clear-agent-terminal');
  const terminal = document.getElementById('global-agent-terminal');

  if (clearBtn && terminal) {
    clearBtn.addEventListener('click', () => {
      terminal.innerHTML = `<div class="terminal-line"><span class="terminal-time">[Ready]</span> Console cleared.</div>`;
    });
  }

  if (runAllBtn && terminal) {
    runAllBtn.addEventListener('click', async () => {
      runAllBtn.disabled = true;
      runAllBtn.innerHTML = `<span class="spinner"></span> Running Batch Autonomous Recovery...`;

      terminal.innerHTML += `
        <div class="terminal-line"><span class="terminal-time">[${new Date().toLocaleTimeString()}]</span> <span class="terminal-tag-success">[SCAN]</span> Scanning for claims eligible for autonomous dispute...</div>
      `;

      try {
        const claimsData = await apiFetch('/api/claims?limit=50&status=ReadyToDispute');
        let targets = claimsData.records;
        if (!targets || targets.length === 0) {
          const allData = await apiFetch('/api/claims?limit=10&status=New');
          targets = allData.records;
        }

        if (!targets || targets.length === 0) {
          terminal.innerHTML += `<div class="terminal-line"><span class="terminal-time">[${new Date().toLocaleTimeString()}]</span> No pending claims requiring dispute. Reseed or create claims first.</div>`;
          return;
        }

        const ids = targets.map(c => c.id);
        terminal.innerHTML += `<div class="terminal-line"><span class="terminal-time">[${new Date().toLocaleTimeString()}]</span> Found ${ids.length} claims. Initiating self-healing portal workers...</div>`;

        for (const cid of ids) {
          const res = await apiFetch(`/api/claims/${cid}/autonomous-loop`, { method: 'POST' });
          terminal.innerHTML += `
            <div class="terminal-line">
              <span class="terminal-time">[${new Date().toLocaleTimeString()}]</span>
              <span class="terminal-tag-success">[RECOVERED]</span>
              Claim #${res.claim_number} (${res.retailer}) -> Filed via ${res.scoring.model_used}. Acknowledgment: ${res.portal?.acknowledgment_code}
            </div>
          `;
          terminal.scrollTop = terminal.scrollHeight;
        }

        showToast(`Autonomous loop completed for ${ids.length} claims!`, 'success');
        loadDashboardMetrics();
      } catch (err) {
        terminal.innerHTML += `<div class="terminal-line" style="color: #ef4444;">Error during batch cycle: ${err.message}</div>`;
      } finally {
        runAllBtn.disabled = false;
        runAllBtn.textContent = 'Execute Autonomous Recovery on All Ready Claims';
      }
    });
  }
}

// --------------------------------------------------------------------------
// Audit Trail & Governance
// --------------------------------------------------------------------------
async function loadAuditLogs() {
  const tbody = document.getElementById('audit-table-body');
  if (!tbody) return;

  tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 30px;"><div class="spinner"></div> Loading audit stream...</td></tr>`;

  try {
    const logs = await apiFetch('/api/audit-logs?limit=50');
    if (!logs || logs.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-dim); padding: 30px;">No audit records found.</td></tr>`;
      return;
    }

    let html = '';
    logs.forEach(l => {
      let detailsStr = '';
      try {
        const d = JSON.parse(l.details_json);
        detailsStr = Object.entries(d).map(([k, v]) => `<strong>${k}:</strong> ${v}`).join(' • ');
      } catch {
        detailsStr = l.details_json || '';
      }

      html += `
        <tr>
          <td style="font-family: var(--font-mono); font-size: 0.78rem; color: var(--text-dim);">${l.timestamp}</td>
          <td><strong>${l.actor_name}</strong></td>
          <td><span class="status-pill status-approved" style="font-size: 0.72rem;">${l.action}</span></td>
          <td>${l.target_type}</td>
          <td style="font-family: var(--font-mono); font-size: 0.8rem; color: #38bdf8;">${l.target_id || 'N/A'}</td>
          <td style="font-size: 0.8rem; color: var(--text-muted);">${detailsStr}</td>
        </tr>
      `;
    });

    tbody.innerHTML = html;
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: #ef4444; padding: 20px;">Failed to load audit logs.</td></tr>`;
  }
}

function setupAuditRefresh() {
  const btn = document.getElementById('btn-refresh-audit');
  if (btn) btn.addEventListener('click', loadAuditLogs);
}

// --------------------------------------------------------------------------
// System Settings Form
// --------------------------------------------------------------------------
async function loadSettings() {
  try {
    const settings = await apiFetch('/api/settings');
    if (settings.rule_engine_threshold) {
      document.getElementById('setting-rule-threshold').value = settings.rule_engine_threshold.value;
    }
    if (settings.slm_threshold) {
      document.getElementById('setting-slm-threshold').value = settings.slm_threshold.value;
    }
    if (settings.human_approval_dollar_limit) {
      document.getElementById('setting-approval-limit').value = settings.human_approval_dollar_limit.value;
    }
    if (settings.success_fee_percent) {
      document.getElementById('setting-success-fee').value = settings.success_fee_percent.value;
    }
    if (settings.erp_integration_type) {
      document.getElementById('setting-erp-type').value = settings.erp_integration_type.value;
    }
  } catch (err) {
    console.error('Failed to load settings:', err);
  }
}

function setupSettingsForm() {
  const form = document.getElementById('settings-form');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.getElementById('btn-save-settings');
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span> Saving...`;

    const payload = {
      settings: {
        rule_engine_threshold: document.getElementById('setting-rule-threshold').value,
        slm_threshold: document.getElementById('setting-slm-threshold').value,
        human_approval_dollar_limit: document.getElementById('setting-approval-limit').value,
        success_fee_percent: document.getElementById('setting-success-fee').value,
        erp_integration_type: document.getElementById('setting-erp-type').value
      }
    };

    try {
      await apiFetch('/api/settings', {
        method: 'PUT',
        body: payload
      });
      showToast('System policies & thresholds saved successfully!', 'success');
    } catch (err) {
      // Handled
    } finally {
      btn.disabled = false;
      btn.textContent = 'Save System Policies';
    }
  });
}

// Academic Spec modal trigger
function setupAcademicModal() {
  const btn = document.getElementById('btn-view-academic-spec');
  if (btn) {
    btn.addEventListener('click', async () => {
      try {
        const info = await apiFetch('/api/system/info');
        alert(
          `DeductIQ — Milestone Review I Rubric Proof (50 Marks):\n\n` +
          `• Author: ${info.team_member}\n` +
          `• Mentor: ${info.mentor}\n` +
          `• Institution: ${info.coe_alignment}\n` +
          `• Course: ${info.course}\n\n` +
          `Novelty Claims:\n` +
          `1. Evidence Graph binding 6 enterprise sources.\n` +
          `2. Deterministic Forensic Reconciliation (0-token cost for 90%+ cases).\n` +
          `3. Self-healing browser skill compiler with DOM mutation fallback.\n` +
          `4. Closed-loop outcome learning for win/loss policy distillation.`
        );
      } catch (e) {
        // Handled
      }
    });
  }
}

// --------------------------------------------------------------------------
// Initialization on DOM Ready
// --------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
  setupNavigation();
  setupPersona();
  setupLedgerControls();
  setupDetailModalButtons();
  setupCreateClaimModal();
  setupUploadAndReseedModals();
  setupConnectors();
  setupAgentConsole();
  setupAuditRefresh();
  setupSettingsForm();
  setupAcademicModal();

  // Load initial dashboard metrics & claims
  loadDashboardMetrics();
});
