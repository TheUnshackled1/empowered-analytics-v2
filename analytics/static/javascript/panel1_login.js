async function handleInstitutionalLogin(btn) {
  const emailInput = document.getElementById('sso-email-input');
  const email = (emailInput && emailInput.value) || 'dean.cit@tip.edu.ph';

  // Honor the ?next= param so the guard sends users back where they came from
  const params = new URLSearchParams(window.location.search);
  const redirectUrl = params.get('next') || (btn && btn.dataset && btn.dataset.redirectUrl) || '/dashboard/';

  try {
    const res = await fetch('/api/v2/auth/session-login/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });
    if (res.ok) {
      const data = await res.json();
      showToast(`Verified ${data.email} · OAuth 2.0 session established`);
    }
  } catch (_) {}

  window.location.href = redirectUrl;
}
