function togglePasswordVisibility() {
  const passInput = document.getElementById('sso-password-input');
  const toggleBtn = document.getElementById('sso-password-toggle');
  const eyeOpen = document.getElementById('eye-icon-open');
  const eyeClosed = document.getElementById('eye-icon-closed');
  if (!passInput) return;

  const isMasked = passInput.type === 'password';
  passInput.type = isMasked ? 'text' : 'password';

  if (eyeOpen && eyeClosed) {
    eyeOpen.classList.toggle('is-hidden', isMasked);
    eyeClosed.classList.toggle('is-hidden', !isMasked);
  }
  if (toggleBtn) {
    const nextLabel = isMasked ? 'Hide password' : 'Show password';
    toggleBtn.setAttribute('aria-label', nextLabel);
    toggleBtn.setAttribute('title', nextLabel);
  }
}

function clearLoginInputErrors() {
  const emailInput = document.getElementById('sso-email-input');
  const passInput = document.getElementById('sso-password-input');
  if (emailInput) emailInput.classList.remove('input-error');
  if (passInput) passInput.classList.remove('input-error');
}

function markLoginInputErrors() {
  const emailInput = document.getElementById('sso-email-input');
  const passInput = document.getElementById('sso-password-input');
  if (emailInput) emailInput.classList.add('input-error');
  if (passInput) passInput.classList.add('input-error');
}

async function handleInstitutionalLogin(btn) {
  const emailInput = document.getElementById('sso-email-input');
  const passInput = document.getElementById('sso-password-input');
  const email = (emailInput && emailInput.value.trim()) || '';
  const password = (passInput && passInput.value) || '';

  clearLoginInputErrors();

  if (!email || !email.includes('@')) {
    markLoginInputErrors();
    showToast('Please enter a valid T.I.P. institutional email address.', 'warn');
    return;
  }
  if (!password) {
    markLoginInputErrors();
    showToast('Please enter your institutional password.', 'warn');
    return;
  }

  // Honor the ?next= param so the guard sends users back where they came from
  const params = new URLSearchParams(window.location.search);
  const nextParam = params.get('next');
  const submitBtn = btn || document.getElementById('btn-sso-submit');
  const defaultUrl = (submitBtn && submitBtn.dataset && submitBtn.dataset.redirectUrl) || '/dashboard/';
  const redirectUrl = nextParam && nextParam !== '/login/' ? nextParam : defaultUrl;

  if (typeof showPageLoader === 'function') {
    showPageLoader('Authenticating T.I.P. OAuth 2.0 + 2FA Session...');
  }

  try {
    const res = await fetch('/api/v2/auth/session-login/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json().catch(() => ({}));
    if (res.ok && data.verified) {
      showToast(`Verified ${data.email} · OAuth 2.0 session established`);
      setTimeout(() => {
        window.location.href = redirectUrl;
      }, 260);
      return;
    }
    if (typeof hidePageLoader === 'function') hidePageLoader();
    markLoginInputErrors();
    showToast(data.detail || 'Invalid institutional username or password. Access denied.', 'error');
  } catch (_) {
    if (typeof hidePageLoader === 'function') hidePageLoader();
    showToast('Unable to reach authentication server.', 'error');
  }
}

function getLoginRedirectUrl(btn) {
  const params = new URLSearchParams(window.location.search);
  const nextParam = params.get('next');
  const submitBtn = btn || document.getElementById('btn-sso-submit');
  const defaultUrl = (submitBtn && submitBtn.dataset && submitBtn.dataset.redirectUrl) || '/dashboard/';
  return nextParam && nextParam !== '/login/' ? nextParam : defaultUrl;
}

function handleMicrosoftOutlookSignIn(btn) {
  const redirectUrl = getLoginRedirectUrl(btn);
  if (btn && btn.dataset && btn.dataset.msOauthEnabled === 'true' && btn.dataset.msLoginUrl) {
    if (typeof showPageLoader === 'function') {
      showPageLoader('Redirecting to Microsoft / Outlook OAuth 2.0...');
    }
    window.location.href = `${btn.dataset.msLoginUrl}?next=${encodeURIComponent(redirectUrl)}`;
    return;
  }
  openMicrosoftOutlookModal();
}

function openMicrosoftOutlookModal() {
  const modal = document.getElementById('ms-outlook-modal');
  if (!modal) return;
  modal.classList.add('show');
  modal.setAttribute('aria-hidden', 'false');
  const input = document.getElementById('ms-outlook-email-input');
  if (input) {
    setTimeout(() => {
      try {
        input.focus();
      } catch (_) {}
    }, 50);
  }
}

function closeMicrosoftOutlookModal() {
  const modal = document.getElementById('ms-outlook-modal');
  if (!modal) return;
  modal.classList.remove('show');
  modal.setAttribute('aria-hidden', 'true');
}

function handleMsModalBackdropClick(event) {
  if (event.target && event.target.id === 'ms-outlook-modal') {
    closeMicrosoftOutlookModal();
  }
}

async function submitMicrosoftOutlookOAuth(presetEmail) {
  const emailInput = document.getElementById('ms-outlook-email-input');
  const email = (presetEmail || (emailInput && emailInput.value) || '').trim();
  if (!email || !email.includes('@')) {
    showToast('Please select an account or enter a valid Microsoft / Outlook email address.', 'warn');
    return;
  }

  const redirectUrl = getLoginRedirectUrl(document.getElementById('btn-ms-outlook-login'));
  closeMicrosoftOutlookModal();
  if (typeof showPageLoader === 'function') {
    showPageLoader(`Authenticating ${email} via Microsoft / Outlook OAuth 2.0...`);
  }

  try {
    const res = await fetch('/api/v2/auth/microsoft-oauth/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });
    const data = await res.json().catch(() => ({}));
    if (res.ok && data.verified) {
      showToast(`Verified ${data.email} · Microsoft / Outlook OAuth 2.0 session established`);
      setTimeout(() => {
        window.location.href = redirectUrl;
      }, 260);
      return;
    }
    if (typeof hidePageLoader === 'function') hidePageLoader();
    showToast(
      data.detail || 'Unable to sign in with that Microsoft / Outlook account.',
      'error'
    );
  } catch (_) {
    if (typeof hidePageLoader === 'function') hidePageLoader();
    showToast('Unable to reach Microsoft / Outlook OAuth server.', 'error');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const emailInput = document.getElementById('sso-email-input');
  const passInput = document.getElementById('sso-password-input');
  [emailInput, passInput].forEach((input) => {
    if (!input) return;
    input.addEventListener('input', clearLoginInputErrors);
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        handleInstitutionalLogin(document.getElementById('btn-sso-submit'));
      }
    });
  });

  const msInput = document.getElementById('ms-outlook-email-input');
  if (msInput) {
    msInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        submitMicrosoftOutlookOAuth();
      }
    });
  }
});
