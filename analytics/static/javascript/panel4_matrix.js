async function cycle(el) {
  const order = ['I', 'E', 'R'];
  const prev = el.textContent.trim();
  const next = order[(order.indexOf(prev) + 1) % 3];
  const courseCode = el.dataset.course;
  const soCode = el.dataset.so;

  el.textContent = next;
  el.className = 'ier-pill tag-' + next;

  if (!courseCode || !soCode) return;

  try {
    const res = await fetch('/api/v2/matrix/mapping/', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ course_code: courseCode, so_code: soCode, proficiency: next }),
    });
    if (res.status === 403) {
      const err = await res.json();
      el.textContent = prev;
      el.className = 'ier-pill tag-' + prev;
      showToast(err.detail || 'RBAC: Level 2 · Write clearance required', 'warn');
      return;
    }
    if (res.ok) {
      const data = await res.json();
      showToast(`${courseCode} · ${soCode} saved as [${next}] (Hash: ${data.sha256_payload})`);
    }
  } catch (_) {}
}

