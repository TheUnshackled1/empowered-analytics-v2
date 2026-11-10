function calcSSR() {
  const boxes = document.querySelectorAll('#crit-box input');
  const checked = Array.from(boxes).filter(b => b.checked).length;
  const pct = Math.round((checked / boxes.length) * 100);
  document.getElementById('ssr-text').textContent = pct + '%';
  document.getElementById('ssr-ring').setAttribute('stroke-dasharray', pct + ', 100');
  document.getElementById('ssr-label').textContent = `${checked} of ${boxes.length} sections locked`;
}

async function downloadABETReport() {
  const boxes = document.querySelectorAll('#crit-box input');
  const criteria = Array.from(boxes).map(b => ({
    code: b.dataset.code,
    title: b.dataset.title,
    locked: b.checked,
  }));
  try {
    const res = await fetch('/api/v2/reports/abet-ssr/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ criteria }),
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
  } catch (_) {}
  window.print();
}

