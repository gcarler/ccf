import { test, type Page, type APIRequestContext } from '@playwright/test';

const email = process.env.E2E_EMAIL || '';
const password = process.env.E2E_PASSWORD || '';
const browserApiBaseUrl = (process.env.NEXT_PUBLIC_API_URL || '/api').replace(/\/$/, '');
const preflightApiBaseUrl = (
  process.env.E2E_API_URL ||
  process.env.API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  ''
).replace(/\/$/, '');
const authE2eEnabled = process.env.E2E_AUTH_ENABLED === '1';

let cachedAccessToken = '';
let cachedRefreshToken: string | null = null;

export function requirePlatformAuthE2E() {
  test.skip(
    !authE2eEnabled || !email || !password || !preflightApiBaseUrl,
    'Set E2E_AUTH_ENABLED=1, E2E_EMAIL, E2E_PASSWORD and E2E_API_URL/NEXT_PUBLIC_API_URL.',
  );
}

export async function preloadPlatformAccessTokens(request: APIRequestContext) {
  if (!preflightApiBaseUrl.startsWith('http')) {
    test.skip(true, 'Use E2E_API_URL/NEXT_PUBLIC_API_URL absoluto para validar login previo.');
    return;
  }

  try {
    const response = await request.post(`${preflightApiBaseUrl}/v3/auth/login`, {
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      data: { email, password },
      timeout: 10_000,
    });
    test.skip(!response.ok(), `Preflight login failed against ${preflightApiBaseUrl}/v3/auth/login`);
    const payload = await response.json();
    cachedAccessToken = payload.access_token;
    cachedRefreshToken = payload.refresh_token ?? null;
  } catch {
    test.skip(true, `Preflight login timeout/unreachable at ${preflightApiBaseUrl}/v3/auth/login`);
  }
}

export async function installPlatformAuthSession(page: Page) {
  await page.addInitScript(
    ({ accessToken, refreshToken }) => {
      sessionStorage.setItem('ccf_token', accessToken);
      if (refreshToken) sessionStorage.setItem('ccf_refresh_token', refreshToken);
    },
    {
      accessToken: cachedAccessToken,
      refreshToken: cachedRefreshToken,
    },
  );
}

export function getPlatformApiBaseUrl() {
  return preflightApiBaseUrl || browserApiBaseUrl;
}
