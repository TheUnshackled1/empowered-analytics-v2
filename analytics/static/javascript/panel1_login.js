async function handleInstitutionalLogin(btn) {
  const emailInput = document.getElementById('sso-email-input');
  const email = (emailInput && emailInput.value) || 'dean.cit@tip.edu.ph';
  const redirectUrl = (btn && btn.dataset && btn.dataset.redirectUrl) || '/dashboard/';

  try {
    const res = await fetch('/api/v2/auth/sso/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });
    if (res.ok) {
      const data = await res.json();
      showToast(`Verified ${data.email} (SHA-256: ${data.sha256_payload})`);
    }
  } catch (_) {}

  window.location.href = redirectUrl;
}

