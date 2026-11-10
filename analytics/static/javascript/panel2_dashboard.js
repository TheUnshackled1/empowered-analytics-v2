window.onCanvasSynced = async function () {
  try {
    const res = await fetch('/api/v2/dashboard/state/');
    if (!res.ok) return;
    const state = await res.json();
    const k = state.kpis;
    if (k) {
      document.getElementById('p2-abet-txt').textContent = k.abet_accreditation + '%';
      document.getElementById('p2-abet-ring').setAttribute('stroke-dasharray', k.abet_accreditation + ', 100');
      document.getElementById('p2-ched-txt').textContent = k.ched_obe_status + '%';
      document.getElementById('p2-ched-ring').setAttribute('stroke-dasharray', k.ched_obe_status + ', 100');
      document.getElementById('p2-cov-txt').textContent = k.matrix_coverage + '%';
      document.getElementById('p2-def-txt').textContent = k.deficit + '%';
    }
    if (state.telemetry) {
      document.getElementById('p2-synced-count').textContent = state.telemetry.total_synced_records;
    }
  } catch (_) {}
};
