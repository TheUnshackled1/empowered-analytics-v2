function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str == null ? '' : String(str);
  return div.innerHTML;
}

function toggleOverviewKeyMask() {
  const input = document.getElementById('api-key-field');
  if (!input) return;
  input.type = input.type === 'password' ? 'text' : 'password';
}

function renderKPIs(kpis) {
  if (!kpis) return;
  document.getElementById('abet-pct').textContent = kpis.abet_accreditation + '%';
  document.getElementById('abet-circle').setAttribute('stroke-dasharray', kpis.abet_accreditation + ', 100');
  document.getElementById('ched-pct').textContent = kpis.ched_obe_status + '%';
  document.getElementById('ched-circle').setAttribute('stroke-dasharray', kpis.ched_obe_status + ', 100');
  document.getElementById('matrix-cov').textContent = kpis.matrix_coverage + '%';
  document.getElementById('deficit-val').textContent = kpis.deficit + '%';
}

function renderCompetenciesAndRadar(comp, radar) {
  if (comp) {
    ['knowledge', 'skills', 'values', 'capstone', 'internship'].forEach(key => {
      const pct = Math.round(Number(comp[key] || 0));
      const valEl = document.getElementById(`comp-${key}-val`);
      const barEl = document.getElementById(`comp-${key}-bar`);
      if (valEl) valEl.textContent = pct + '%';
      if (barEl) barEl.style.width = Math.min(100, Math.max(0, pct)) + '%';
    });
  }
  if (radar) {
    const axes = [
      radar.knowledge,
      radar.problem_solving,
      radar.design,
      radar.communication,
      radar.ethics,
      radar.teamwork,
    ];
    const anglesDeg = [-90, -30, 30, 90, 150, 210];
    const pts = axes.map((pct, idx) => {
      const r = (Math.min(100, Math.max(10, Number(pct ?? 80))) / 100) * 48;
      const rad = (anglesDeg[idx] * Math.PI) / 180;
      return `${(60 + r * Math.cos(rad)).toFixed(1)},${(60 + r * Math.sin(rad)).toFixed(1)}`;
    });
    const poly = document.getElementById('radar-data-poly');
    if (poly) poly.setAttribute('points', pts.join(' '));
  }
}

function renderTelemetry(telemetry) {
  if (!telemetry) return;
  document.getElementById('latency-txt').textContent = telemetry.latency_avg_ms;
  document.getElementById('pkt-txt').textContent = Number(telemetry.throughput_pkts).toFixed(1) + 'k pkt/s';
  const latSeries = telemetry.latency_series || [];
  if (latSeries.length > 1) {
    const maxLat = Math.max(70, ...latSeries);
    const stepX = 260 / (latSeries.length - 1);
    const coords = latSeries.map((ms, i) => `${(i * stepX).toFixed(1)},${(50 - Math.min(42, (ms / maxLat) * 38)).toFixed(1)}`);
    const lineD = 'M' + coords.join(' L');
    document.getElementById('latency-line').setAttribute('d', lineD);
    document.getElementById('latency-area').setAttribute('d', `${lineD} L260,55 L0,55 Z`);
  }
  const pktSeries = telemetry.throughput_series || [];
  if (pktSeries.length) {
    const maxPkt = Math.max(1.8, ...pktSeries);
    document.getElementById('throughput-bars').innerHTML = pktSeries.map(val => {
      const h = Math.max(18, Math.round((val / maxPkt) * 100));
      return `<div class="bar-col" style="height:${h}%; background:var(--emerald);"></div>`;
    }).join('');
  }
}

function renderCourseMatrix(courses) {
  if (!Array.isArray(courses)) return;
  document.getElementById('matrix-body').innerHTML = courses.map(course => {
    const map = {};
    (course.outcomes || []).forEach(o => { map[o.so_code] = o.proficiency; });
    const cells = ['SO1', 'SO2', 'SO3', 'SO4'].map(so => {
      const prof = map[so];
      const attrs = `data-course="${escapeHtml(course.course_code)}" data-so="${so}" onclick="cycleIER(this)"`;
      if (!prof) {
        return `<td><span class="ier-pill tag-none" ${attrs} title="Unmapped · click to map">—</span></td>`;
      }
      return `<td><span class="ier-pill tag-${escapeHtml(prof)}" ${attrs}>${escapeHtml(prof)}</span></td>`;
    }).join('');
    return `<tr><td><strong>${escapeHtml(course.course_code)}</strong><br><span class="course-sub-lbl">${escapeHtml(course.course_title)}</span></td>${cells}</tr>`;
  }).join('');
}

function renderABET(abet) {
  if (!abet) return;
  document.getElementById('ssr-pct').textContent = abet.ssr_pct + '%';
  document.getElementById('ssr-circle').setAttribute('stroke-dasharray', abet.ssr_pct + ', 100');
  document.getElementById('ssr-count').textContent =
    `${abet.locked_count} of ${abet.total_count} sections locked`;
  (abet.criteria || []).forEach(crit => {
    const box = Array.from(document.querySelectorAll('#criteria-list input[type="checkbox"]'))
      .find(b => b.dataset.code === crit.code);
    if (box) box.checked = !!crit.locked;
  });
}

function renderAuditLogs(logs) {
  if (!Array.isArray(logs)) return;
  document.getElementById('audit-body').innerHTML = logs.slice(0, 5).map(log => `
    <tr>
      <td>${escapeHtml(log.timestamp)}</td>
      <td class="hash-cell">${escapeHtml(log.sha256_payload)}</td>
      <td><span class="act-pill">${escapeHtml(log.action)}</span></td>
      <td class="priv-ok">${log.privacy_verified ? '✓' : '—'}</td>
    </tr>
  `).join('');
}

function applyRBACSelectionUI(level) {
  document.querySelectorAll('#rbac-selector .rbac-box').forEach(b => {
    const isMatch = Number(b.dataset.level) === Number(level);
    b.classList.toggle('selected', isMatch);
    b.textContent = isMatch ? b.textContent.replace('○', '●') : b.textContent.replace('●', '○');
  });
}

async function loadDashboardState() {
  const webhookField = document.getElementById('webhook-url-field');
  if (webhookField && window.location.protocol.startsWith('http')) {
    webhookField.value = `${window.location.origin}/api/v2/hooks/canvas-sync/`;
  }
  try {
    const res = await fetch('/api/v2/dashboard/state/');
    if (!res.ok) return;
    const state = await res.json();
    renderKPIs(state.kpis);
    renderCompetenciesAndRadar(state.competencies, state.radar);
    renderTelemetry(state.telemetry);
    renderCourseMatrix(state.course_matrix);
    renderAuditLogs(state.audit_logs);
    renderABET(state.abet);
    if (state.oauth_token_masked) {
      const tokenEl = document.getElementById('sso-token-sub');
      if (tokenEl) tokenEl.textContent = 'Token: ' + state.oauth_token_masked;
    }
    if (state.config) {
      document.getElementById('api-key-field').value = state.config.api_secret_key;
      document.getElementById('sw-latency').classList.toggle('active', !!state.config.alert_high_latency);
      document.getElementById('sw-failure').classList.toggle('active', !!state.config.alert_sync_failure);
      document.getElementById('sw-digest').classList.toggle('active', !!state.config.alert_weekly_digest);
      applyRBACSelectionUI(state.config.active_clearance_level);
    }
    if (state.sso_user && state.sso_user.email) {
      document.getElementById('sso-email').value = state.sso_user.email;
    }
  } catch (_) {}
}

function prependAuditRow(time, hash, action) {
  const tbody = document.getElementById('audit-body');
  if (!tbody) return;
  const tr = document.createElement('tr');
  tr.innerHTML = `
    <td>${escapeHtml(time)}</td>
    <td class="hash-cell">${escapeHtml(hash)}</td>
    <td><span class="act-pill">${escapeHtml(action)}</span></td>
    <td class="priv-ok">✓</td>
  `;
  tbody.insertBefore(tr, tbody.firstChild);
  while (tbody.children.length > 5) tbody.removeChild(tbody.lastChild);
}

async function verifyInstitutionalSSO() {
  const email = document.getElementById('sso-email').value;
  try {
    const res = await fetch('/api/v2/auth/sso/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });
    if (res.ok) {
      const data = await res.json();
      document.getElementById('sso-status-sub').textContent = `Verified at ${data.timestamp} · L${data.clearance_level}`;
      const tokenEl = document.getElementById('sso-token-sub');
      if (tokenEl && data.oauth_token_masked) tokenEl.textContent = 'Token: ' + data.oauth_token_masked;
      prependAuditRow(data.timestamp, data.sha256_payload, data.action);
      showToast(`OAuth 2.0 + 2FA verified (${data.email})`);
    }
  } catch (_) {}
}

const OVERVIEW_MATRIX_CYCLE = ['I', 'E', 'R', '-'];

function overviewMatrixValue(el) {
  const txt = el.textContent.trim();
  return txt === '—' || txt === '' ? '-' : txt;
}

function paintOverviewPill(el, value) {
  el.textContent = value === '-' ? '—' : value;
  el.className = 'ier-pill ' + (value === '-' ? 'tag-none' : 'tag-' + value);
}

async function cycleIER(el) {
  const prev = overviewMatrixValue(el);
  const next = OVERVIEW_MATRIX_CYCLE[(OVERVIEW_MATRIX_CYCLE.indexOf(prev) + 1) % OVERVIEW_MATRIX_CYCLE.length];
  paintOverviewPill(el, next);
  try {
    const res = await fetch('/api/v2/matrix/mapping/', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ course_code: el.dataset.course, so_code: el.dataset.so, proficiency: next }),
    });
    if (res.status === 403) {
      const err = await res.json();
      paintOverviewPill(el, prev);
      showToast(err.detail || 'RBAC: Write clearance required', 'warn');
      return;
    }
    if (res.ok) {
      const data = await res.json();
      renderKPIs(data.kpis);
      prependAuditRow(data.timestamp, data.sha256_payload, data.action);
      const label = next === '-' ? 'cleared' : `updated to [${next}]`;
      showToast(`${el.dataset.course} · ${el.dataset.so} ${label}`);
      return;
    }
    paintOverviewPill(el, prev);
  } catch (_) {
    paintOverviewPill(el, prev);
  }
}

async function toggleCriterionOverview(box) {
  const wanted = box.checked;
  try {
    const res = await fetch('/api/v2/abet/criteria/', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code: box.dataset.code, locked: wanted }),
    });
    if (res.status === 403) {
      const err = await res.json();
      box.checked = !wanted;
      showToast(err.detail || 'RBAC: Level 2 clearance required', 'warn');
      return;
    }
    if (res.ok) {
      const data = await res.json();
      renderABET(data.abet);
      renderKPIs(data.kpis);
      prependAuditRow(data.timestamp, data.sha256_payload, data.action);
      showToast(`${data.code} ${data.locked ? 'locked' : 'reopened'} · saved`);
      return;
    }
    box.checked = !wanted;
  } catch (_) {
    box.checked = !wanted;
  }
}

async function openOverviewPrintPreview(event) {
  if (event) event.preventDefault();
  try {
    const res = await fetch('/api/v2/reports/abet-print-seal/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });
    if (res.ok) {
      const data = await res.json();
      prependAuditRow(data.timestamp, data.sha256_payload, data.action);
      showToast('Printable SSR sealed & logged');
      window.open('/abet-report/print/?seal=' + encodeURIComponent(data.sha256_payload), '_blank');
    }
  } catch (_) {}
}

async function setRBAC(el, level) {
  const previous = Number(document.querySelector('#rbac-selector .rbac-box.selected')?.dataset.level || 2);
  applyRBACSelectionUI(level);
  try {
    const res = await fetch('/api/v2/config/settings/', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ active_clearance_level: level }),
    });
    if (res.ok) {
      const data = await res.json();
      if (data.sha256_payload) prependAuditRow(data.timestamp, data.sha256_payload, data.action);
      showToast(`Clearance switched to Level ${level}`);
      return;
    }
    applyRBACSelectionUI(previous);
  } catch (_) {
    applyRBACSelectionUI(previous);
  }
}

async function toggleAlertSwitch(el, fieldName) {
  const nextState = !el.classList.contains('active');
  el.classList.toggle('active', nextState);
  try {
    const res = await fetch('/api/v2/config/settings/', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ [fieldName]: nextState }),
    });
    if (res.status === 403) {
      const err = await res.json();
      el.classList.toggle('active', !nextState);
      showToast(err.detail || 'RBAC: Level 2 clearance required', 'warn');
      return;
    }
    if (res.ok) {
      const data = await res.json();
      if (data.sha256_payload) prependAuditRow(data.timestamp, data.sha256_payload, data.action);
    }
  } catch (_) {}
}

async function exportABETReport() {
  // Server compiles the PDF from the persisted ABET checklist.
  try {
    const res = await fetch('/api/v2/reports/abet-ssr/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });
    if (res.ok) {
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'TIP_EmpowerED_ABET_SSR_v2.pdf';
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      prependAuditRow(res.headers.get('X-Audit-Timestamp') || '', res.headers.get('X-Audit-Hash') || '', 'EXPORT · PDF');
      showToast('ABET SSR PDF downloaded & logged');
    }
  } catch (_) {}
}

async function rotateApiKey() {
  try {
    const res = await fetch('/api/v2/config/rotate-key/', { method: 'POST', headers: { 'Content-Type': 'application/json' } });
    if (res.status === 403) {
      const err = await res.json();
      showToast(err.detail || 'RBAC: Level 3 · Admin required', 'warn');
      return;
    }
    if (res.ok) {
      const data = await res.json();
      const keyField = document.getElementById('api-key-field');
      keyField.value = data.api_secret_key;
      keyField.type = 'text';
      setTimeout(() => { keyField.type = 'password'; }, 2800);
      prependAuditRow(data.timestamp, data.sha256_payload, data.action);
      showToast('API Secret Key rotated');
    }
  } catch (_) {}
}

window.onCanvasSynced = function () {
  loadDashboardState();
};

document.addEventListener('DOMContentLoaded', () => {
  loadDashboardState();
});

