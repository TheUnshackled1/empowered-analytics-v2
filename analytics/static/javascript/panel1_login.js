async function handleInstitutionalLogin(btn) {
  const emailInput = document.getElementById('sso-email-input');
  const passInput = document.getElementById('sso-password-input');
  const email = (emailInput && emailInput.value.trim()) || '';
  const password = (passInput && passInput.value) || '';

  if (!email || !email.includes('@')) {
    showToast('Please enter a valid T.I.P. institutional email address.', 'warn');
    return;
  }
  if (!password) {
    showToast('Please enter your institutional password.', 'warn');
    return;
  }

  // Honor the ?next= param so the guard sends users back where they came from
  const params = new URLSearchParams(window.location.search);
  const nextParam = params.get('next');
  const defaultUrl = (btn && btn.dataset && btn.dataset.redirectUrl) || '/dashboard/';
  const redirectUrl = nextParam && nextParam !== '/login/' ? nextParam : defaultUrl;

  try {
    const res = await fetch('/api/v2/auth/session-login/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });
    if (res.ok) {
      const data = await res.json();
      showToast(`Verified ${data.email} · OAuth 2.0 session established`);
      window.location.href = redirectUrl;
      return;
    }
    showToast('Authentication failed. Please verify your credentials.', 'error');
  } catch (_) {
    showToast('Unable to reach authentication server.', 'error');
  }
}
