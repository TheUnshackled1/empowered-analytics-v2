const GLOBAL_SYNC_COURSES = ['CPE 515', 'CPE 616', 'CPE 412', 'CPE 512', 'CPE 311'];
let globalSyncIdx = 0;
let modalDismissTimer = null;

const MODAL_ICONS = {
  error: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
  warn: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
  ok: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
  info: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>',
};

const MODAL_DEFAULTS = {
  error: {
    title: 'Access Denied',
    subtitle: 'T.I.P. EmpowerED Security & Policy Guard',
    btnText: 'Dismiss',
  },
  warn: {
    title: 'Clearance Warning',
    subtitle: 'Role-Based Access Control (RBAC)',
    btnText: 'Acknowledge',
  },
  ok: {
    title: 'Action Completed',
    subtitle: 'T.I.P. EmpowerED System Telemetry',
    btnText: 'Dismiss',
  },
  info: {
    title: 'System Notice',
    subtitle: 'T.I.P. Institutional Framework',
    btnText: 'Dismiss',
  },
};

function showAlertModal(message, variant = 'ok', customTitle = null) {
  const modal = document.getElementById('system-alert-modal');
  const card = document.getElementById('system-modal-card');
  const titleEl = document.getElementById('system-modal-title');
  const subEl = document.getElementById('system-modal-subtitle');
  const msgEl = document.getElementById('system-modal-message');
  const iconEl = document.getElementById('system-modal-icon');
  const btnEl = document.getElementById('system-modal-action-btn');

  if (!modal || !card) {
    fallbackToast(message, variant);
    return;
  }

  if (modalDismissTimer) {
    clearTimeout(modalDismissTimer);
    modalDismissTimer = null;
  }

  const normalizedVariant = ['error', 'warn', 'ok', 'info'].includes(variant) ? variant : 'ok';
  const defaults = MODAL_DEFAULTS[normalizedVariant];

  card.className = `system-modal-card ${normalizedVariant}`;
  if (titleEl) titleEl.textContent = customTitle || defaults.title;
  if (subEl) subEl.textContent = defaults.subtitle;
  if (msgEl) msgEl.textContent = message;
  if (iconEl) iconEl.innerHTML = MODAL_ICONS[normalizedVariant] || MODAL_ICONS.info;
  if (btnEl) btnEl.textContent = defaults.btnText;

  modal.classList.remove('closing');
  modal.classList.add('show');
  modal.setAttribute('aria-hidden', 'false');

  if (btnEl) {
    setTimeout(() => {
      try {
        btnEl.focus();
      } catch (_) {}
    }, 40);
  }
}

function closeSystemModal() {
  const modal = document.getElementById('system-alert-modal');
  if (!modal || !modal.classList.contains('show')) return;

  modal.classList.add('closing');
  setTimeout(() => {
    modal.classList.remove('show', 'closing');
    modal.setAttribute('aria-hidden', 'true');
  }, 200);
}

function handleModalBackdropClick(event) {
  if (event.target && event.target.id === 'system-alert-modal') {
    closeSystemModal();
  }
}

function fallbackToast(message, variant = 'ok') {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const div = document.createElement('div');
  div.className = 'toast-msg' + (variant === 'warn' ? ' warn' : variant === 'error' ? ' error' : '');
  div.textContent = message;
  container.appendChild(div);
  setTimeout(() => {
    if (div.parentNode) div.parentNode.removeChild(div);
  }, 3600);
}

function showToast(message, variant = 'ok') {
  showAlertModal(message, variant);
}

function showPageLoader(subtitleText = 'Synchronizing module state...') {
  const overlay = document.getElementById('page-transition-loader');
  const progress = document.getElementById('page-progress-bar');
  const sub = document.getElementById('loader-subtext');

  if (sub && subtitleText) {
    sub.textContent = subtitleText;
  }
  if (progress) {
    progress.classList.remove('complete');
    progress.classList.add('active');
  }
  if (overlay) {
    overlay.classList.add('active');
  }
}

function hidePageLoader() {
  const overlay = document.getElementById('page-transition-loader');
  const progress = document.getElementById('page-progress-bar');

  if (progress && progress.classList.contains('active')) {
    progress.classList.add('complete');
    setTimeout(() => {
      progress.classList.remove('active', 'complete');
    }, 240);
  }
  if (overlay) {
    overlay.classList.remove('active');
  }
}

function navigateWithTransition(targetUrl, labelText) {
  if (!targetUrl) return;
  showPageLoader(labelText || 'Loading module...');
  setTimeout(() => {
    window.location.href = targetUrl;
  }, 240);
}

document.addEventListener('DOMContentLoaded', () => {
  hidePageLoader();

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      const modal = document.getElementById('system-alert-modal');
      if (modal && modal.classList.contains('show')) {
        e.preventDefault();
        closeSystemModal();
      }
    }
  });

  const navLinks = document.querySelectorAll('.module-nav .nav-item, #logout-btn, .topbar .brand');
  navLinks.forEach((link) => {
    link.addEventListener('click', (e) => {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) {
        return;
      }
      const href = link.getAttribute('href');
      if (!href || href.startsWith('#') || href.startsWith('javascript:')) {
        return;
      }
      // Avoid redundant transition if already on the exact same pathname
      const destUrl = new URL(href, window.location.origin);
      if (destUrl.pathname === window.location.pathname && destUrl.search === window.location.search) {
        return;
      }

      e.preventDefault();
      let label = 'Synchronizing module state...';
      if (link.id === 'logout-btn') {
        label = 'Signing out of EmpowerED session...';
      } else {
        const navLabel = link.querySelector('.nav-label');
        if (navLabel && navLabel.textContent.trim()) {
          label = `Loading ${navLabel.textContent.trim()}...`;
        }
      }
      navigateWithTransition(href, label);
    });
  });
});

window.addEventListener('pageshow', () => {
  hidePageLoader();
});

async function triggerGlobalSync() {
  const btn = document.getElementById('sync-btn');
  const courseCode = GLOBAL_SYNC_COURSES[globalSyncIdx % GLOBAL_SYNC_COURSES.length];
  globalSyncIdx += 1;
  if (btn) btn.textContent = `⏳ Syncing Canvas LTI 1.3 (${courseCode})...`;

  try {
    const headers = { 'Content-Type': 'application/json' };
    const keyInput = document.getElementById('api-key-field');
    if (keyInput && keyInput.value) {
      headers['Authorization'] = `Bearer ${keyInput.value}`;
    }

    const res = await fetch('/api/v2/hooks/canvas-sync/', {
      method: 'POST',
      headers,
      body: JSON.stringify({
        course_code: courseCode,
        canvas_rubric_id: 'RUB-2026-' + Math.floor(100 + Math.random() * 900),
        student_number: '2023-' + Math.floor(10000 + Math.random() * 90000),
        scores: {
          knowledge: 88 + Math.floor(Math.random() * 8),
          skills: 80 + Math.floor(Math.random() * 10),
          values: 86 + Math.floor(Math.random() * 8),
          capstone: 76 + Math.floor(Math.random() * 12),
          internship: 93 + Math.floor(Math.random() * 6),
        },
      }),
    });

    if (res.ok) {
      const data = await res.json();
      data.course_code = courseCode;
      if (btn) btn.textContent = `✓ Synced (${data.latency_ms} ms) | Hash: ${data.sha256_payload}`;
      showToast(`Canvas LMS synced (${courseCode}) in ${data.latency_ms} ms`);
      if (typeof window.onCanvasSynced === 'function') {
        window.onCanvasSynced(data);
      }
      return;
    }
  } catch (_) {}

  if (btn) btn.textContent = '● Live Sync Complete';
  showToast(`Simulated Canvas sync (${courseCode})`);
}
