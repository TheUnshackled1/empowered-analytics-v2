const MATRIX_CYCLE = ['I', 'E', 'R', '-'];

function matrixValueOf(el) {
  const txt = el.textContent.trim();
  return txt === '—' || txt === '' ? '-' : txt;
}

function paintMatrixPill(el, value) {
  el.textContent = value === '-' ? '—' : value;
  el.className = 'ier-pill ' + (value === '-' ? 'tag-none' : 'tag-' + value);
}

async function cycle(el) {
  const prev = matrixValueOf(el);
  const next = MATRIX_CYCLE[(MATRIX_CYCLE.indexOf(prev) + 1) % MATRIX_CYCLE.length];
  const courseCode = el.dataset.course;
  const soCode = el.dataset.so;

  paintMatrixPill(el, next);

  if (!courseCode || !soCode) return;

  try {
    const res = await fetch('/api/v2/matrix/mapping/', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ course_code: courseCode, so_code: soCode, proficiency: next }),
    });
    if (res.status === 403) {
      const err = await res.json();
      paintMatrixPill(el, prev);
      showToast(err.detail || 'RBAC: Level 2 · Write clearance required', 'warn');
      return;
    }
    if (res.ok) {
      const data = await res.json();
      const label = next === '-' ? 'cleared' : `saved as [${next}]`;
      showToast(`${courseCode} · ${soCode} ${label} (Hash: ${data.sha256_payload})`);
      return;
    }
    paintMatrixPill(el, prev);
  } catch (_) {
    paintMatrixPill(el, prev);
  }
}
