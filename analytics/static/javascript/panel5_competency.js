function updateRadarPolygon(radar) {
  if (!radar) return;
  const axes = [
    radar.knowledge ?? 88,
    radar.problem_solving ?? 82,
    radar.design ?? 74,
    radar.communication ?? 89,
    radar.ethics ?? 85,
    radar.teamwork ?? 90,
  ];
  const anglesDeg = [-90, -30, 30, 90, 150, 210];
  const pts = axes.map((pct, i) => {
    const r = (Math.min(100, Math.max(10, Number(pct))) / 100) * 48;
    const rad = (anglesDeg[i] * Math.PI) / 180;
    return `${(60 + r * Math.cos(rad)).toFixed(1)},${(60 + r * Math.sin(rad)).toFixed(1)}`;
  });
  const poly = document.getElementById('p5-radar-poly');
  if (poly) poly.setAttribute('points', pts.join(' '));
}

async function hydrateCompetencies() {
  try {
    const res = await fetch('/api/v2/dashboard/state/');
    if (!res.ok) return;
    const state = await res.json();
    const c = state.competencies;
    if (c) {
      ['knowledge', 'skills', 'values', 'capstone', 'internship'].forEach(k => {
        const pct = Math.round(Number(c[k] || 0));
        document.getElementById(`p5-val-${k}`).textContent = pct + '%';
        document.getElementById(`p5-bar-${k}`).style.width = pct + '%';
      });
      document.getElementById('p5-lbl-know').textContent = `Knowledge (${Math.round(c.knowledge)}%)`;
    }
    updateRadarPolygon(state.radar);
  } catch (_) {}
}

window.onCanvasSynced = hydrateCompetencies;
document.addEventListener('DOMContentLoaded', hydrateCompetencies);

