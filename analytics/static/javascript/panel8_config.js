function toggleKeyVisibility(inputEl) {
  if (!inputEl) return;
  inputEl.type = inputEl.type === 'password' ? 'text' : 'password';
}

async function selectRole(el, level) {
  Array.from(el.parentElement.children).forEach(c => {
    c.classList.remove('selected');
    c.textContent = c.textContent.trim().replace('●', '○');
  });
  el.classList.add('selected');
  el.textContent = el.textContent.trim().replace('○', '●');

  try {
    const res = await fetch('/api/v2/config/settings/', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ active_clearance_level: level }),
    });
    if (res.ok) {
      const names = { 1: 'Level 1 · Read', 2: 'Level 2 · Write', 3: 'Level 3 · Admin' };
      showToast(`Active clearance set to ${names[level]}`);
    }
  } catch (_) {}
}

async function toggleConfigSwitch(el, fieldName) {
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
    }
  } catch (_) {}
}

async function rotateSecretKey() {
  try {
    const res = await fetch('/api/v2/config/rotate-key/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    if (res.status === 403) {
      const err = await res.json();
      showToast(err.detail || 'RBAC: Select Level 3 · Admin to rotate secret key', 'warn');
      return;
    }
    if (res.ok) {
      const data = await res.json();
      const input = document.getElementById('api-key-field');
      input.value = data.api_secret_key;
      input.type = 'text';
      setTimeout(() => { input.type = 'password'; }, 3000);
      showToast(`API Secret Key rotated & logged (Hash: ${data.sha256_payload})`);
    }
  } catch (_) {}
}

