async function refreshPipelineSparkline() {
  try {
    const res = await fetch('/api/v2/dashboard/state/');
    if (!res.ok) return;
    const state = await res.json();
    const series = state.telemetry && state.telemetry.latency_series;
    if (Array.isArray(series) && series.length > 1) {
      const maxLat = Math.max(70, ...series);
      const stepX = 260 / (series.length - 1);
      const coords = series.map((ms, i) => {
        const x = (i * stepX).toFixed(1);
        const y = (50 - Math.min(42, (ms / maxLat) * 38)).toFixed(1);
        return `${x},${y}`;
      });
      const lineD = 'M' + coords.join(' L');
      document.getElementById('p3-latency-line').setAttribute('d', lineD);
      document.getElementById('p3-latency-area').setAttribute('d', `${lineD} L260,55 L0,55 Z`);
    }
  } catch (_) {}
}

window.onCanvasSynced = function (data) {
  document.getElementById('page-latency').textContent = data.latency_ms;
  if (data.throughput_pkts) {
    document.getElementById('page-throughput').textContent = Number(data.throughput_pkts).toFixed(1) + 'k pkt/s';
  }
  document.getElementById('payload-preview').textContent =
    `[API 200] OAuth 2.0 Handshake Verified (${data.timestamp})\n` +
    `[ETL] Course: ${data.course_code || 'CPE 515'} -> SO1..SO4 (${data.latency_ms} ms)\n` +
    `[DPA] RA 10173 SHA-256 Anonymization: ${data.sha256_payload}\n` +
    `[SIS] Status: ${data.status}`;
  refreshPipelineSparkline();
};

document.addEventListener('DOMContentLoaded', refreshPipelineSparkline);

