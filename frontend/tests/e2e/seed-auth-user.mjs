const apiBase = (process.env.E2E_API_URL || process.env.NEXT_PUBLIC_API_URL || '').replace(/\/$/, '');
const email = process.env.E2E_EMAIL || '';
const password = process.env.E2E_PASSWORD || '';
const username = process.env.E2E_USERNAME || 'e2e_user';

if (!apiBase || !email || !password) {
  console.log('[seed-auth-user] Missing env vars, skipping seed.');
  process.exit(0);
}

const loginForm = new URLSearchParams();
loginForm.set('username', email);
loginForm.set('password', password);

async function tryLogin() {
  const response = await fetch(`${apiBase}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8' },
    body: loginForm,
  });
  return response.ok;
}

async function tryRegister() {
  const payload = {
    username,
    email,
    password,
    role: 'estudiante',
  };

  const response = await fetch(`${apiBase}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify(payload),
  });

  if (response.ok) return true;
  const text = await response.text();
  if (text.toLowerCase().includes('registrado') || text.toLowerCase().includes('exists')) {
    return true;
  }
  throw new Error(`[seed-auth-user] Register failed: ${response.status} ${text}`);
}

async function main() {
  try {
    const loginOk = await tryLogin();
    if (loginOk) {
      console.log('[seed-auth-user] User already valid.');
      return;
    }

    await tryRegister();
    const loginAfterRegister = await tryLogin();
    if (!loginAfterRegister) {
      throw new Error('[seed-auth-user] Login still failing after register.');
    }
    console.log('[seed-auth-user] User created and validated.');
  } catch (error) {
    console.error(error);
    process.exit(1);
  }
}

await main();
