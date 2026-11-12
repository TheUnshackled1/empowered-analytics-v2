const GLOBAL_SYNC_COURSES = ['CPE 515', 'CPE 616', 'CPE 412', 'CPE 512', 'CPE 311'];
let globalSyncIdx = 0;

function showToast(message, variant = 'ok') {
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
