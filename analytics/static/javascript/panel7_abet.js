function renderSSR(abet) {
  if (!abet) return;
  document.getElementById('ssr-text').textContent = abet.ssr_pct + '%';
  document.getElementById('ssr-ring').setAttribute('stroke-dasharray', abet.ssr_pct + ', 100');
  document.getElementById('ssr-label').textContent =
    `${abet.locked_count} of ${abet.total_count} sections locked`;
}

async function toggleCriterion(box) {
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
      renderSSR(data.abet);
      showToast(
        `${data.code} ${data.locked ? 'locked' : 'reopened'} · saved (Hash: ${data.sha256_payload})`
      );
      return;
    }
    box.checked = !wanted;
    showToast('Unable to save ABET checklist.', 'error');
  } catch (_) {
    box.checked = !wanted;
    showToast('Unable to reach server.', 'error');
  }
}

async function downloadABETReport() {
  // The server compiles the PDF from the persisted checklist, not from browser state.
  try {
    const res = await fetch('/api/v2/reports/abet-ssr/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });
    if (res.ok) {
      const blob = await res.blob();
      const hash = res.headers.get('X-Audit-Hash') || '';
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'TIP_EmpowerED_ABET_SSR_v2.pdf';
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      showToast(`ABET SSR PDF downloaded & logged (${hash})`);
      return;
    }
    showToast('PDF export failed.', 'error');
  } catch (_) {
    showToast('Unable to reach server.', 'error');
  }
}

async function openPrintPreview() {
  try {
    const res = await fetch('/api/v2/reports/abet-print-seal/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });
    if (res.ok) {
      const data = await res.json();
      showToast(`Printable SSR sealed & logged (${data.sha256_payload})`);
      window.open('/abet-report/print/?seal=' + encodeURIComponent(data.sha256_payload), '_blank');
      return;
    }
  } catch (_) {}
  showToast('Unable to seal printable report.', 'error');
}
