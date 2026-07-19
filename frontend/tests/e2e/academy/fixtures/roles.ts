// TKT-202 — Multi-role Playwright fixtures for the Academy module (FINAL v3).
//
// Pivot from previous Object.fromEntries + mapped-type cast approach which
// produced TS2322 (TestFixtureValue ↔ TestFixture<T> incompatibility).
// Inline 8 explicit fixtures: simpler, TS-safe, no exotic generics.
//
// Persona → Platform role mapping (canonical DEFAULT_ROLES):
//   lector      → LECTOR           (academy:read)
//   estudiante  → MIEMBRO          (academy:study)
//   maestro     → DOCENTE          (custom idempotent; academy:read+edit)
//   admin       → ADMINISTRADOR    (academy:manage)

import {
  test as base,
  request as pwRequest,
  expect,
  type Page,
  type APIRequestContext,
} from '@playwright/test';

// Re-export Page + APIRequestContext so spec files can
//   `import { test, expect, type Page, type APIRequestContext } from './fixtures/roles'`
export type { Page, APIRequestContext };

const ACADEMY_PASSWORD =
  process.env.ACADEMY_SEED_PASSWORD || 'E2E-Academy-2026!';

function resolveApiBaseUrl(): string {
  return (
    process.env.E2E_API_URL ||
    process.env.API_BASE_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    ''
  ).replace(/\/$/, '');
}

async function login(
  email: string,
): Promise<{ accessToken: string; refreshToken: string | null }> {
  const apiBase = resolveApiBaseUrl();
  test.skip(
    !apiBase || !apiBase.startsWith('http'),
    'Set E2E_API_URL (absolute) so seed-academy-roles + login can run.',
  );

  const response = await fetch(`${apiBase}/v3/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ email, password: ACADEMY_PASSWORD }),
  });
  test.skip(
    !response.ok,
    `Login failed for ${email} (HTTP ${response.status}) — run seed-academy-roles.mjs first.`,
  );
  const payload = (await response.json()) as {
    access_token: string;
    refresh_token?: string;
  };
  return { accessToken: payload.access_token, refreshToken: payload.refresh_token ?? null };
}

// Each `*Page` fixture logs the role user in and writes tokens to
// sessionStorage so AuthContext bootstraps on first paint.
export const test = base.extend<
  {
    lectorPage: Page;
    estudiantePage: Page;
    maestroPage: Page;
    adminPage: Page;
    lectorRequest: APIRequestContext;
    estudianteRequest: APIRequestContext;
    maestroRequest: APIRequestContext;
    adminRequest: APIRequestContext;
  }
>({
  lectorPage: async ({ browser }, use) => {
    const { accessToken, refreshToken } = await login('e2e.lector@ccf.local');
    const context = await browser.newContext();
    await context.addInitScript(
      ({ accessToken: token, refreshToken: rt }) => {
        try {
          sessionStorage.setItem('ccf_token', token);
          if (rt) {
            sessionStorage.setItem('ccf_refresh_token', rt);
          }
        } catch {
          /* context may be torn down */
        }
      },
      { accessToken, refreshToken },
    );
    const page = await context.newPage();
    try {
      await use(page);
    } finally {
      await page.context().close();
    }
  },
  estudiantePage: async ({ browser }, use) => {
    const { accessToken, refreshToken } = await login('e2e.estudiante@ccf.local');
    const context = await browser.newContext();
    await context.addInitScript(
      ({ accessToken: token, refreshToken: rt }) => {
        try {
          sessionStorage.setItem('ccf_token', token);
          if (rt) {
            sessionStorage.setItem('ccf_refresh_token', rt);
          }
        } catch {
          /* context may be torn down */
        }
      },
      { accessToken, refreshToken },
    );
    const page = await context.newPage();
    try {
      await use(page);
    } finally {
      await page.context().close();
    }
  },
  maestroPage: async ({ browser }, use) => {
    const { accessToken, refreshToken } = await login('e2e.maestro@ccf.local');
    const context = await browser.newContext();
    await context.addInitScript(
      ({ accessToken: token, refreshToken: rt }) => {
        try {
          sessionStorage.setItem('ccf_token', token);
          if (rt) {
            sessionStorage.setItem('ccf_refresh_token', rt);
          }
        } catch {
          /* context may be torn down */
        }
      },
      { accessToken, refreshToken },
    );
    const page = await context.newPage();
    try {
      await use(page);
    } finally {
      await page.context().close();
    }
  },
  adminPage: async ({ browser }, use) => {
    const { accessToken, refreshToken } = await login('e2e.admin@ccf.local');
    const context = await browser.newContext();
    await context.addInitScript(
      ({ accessToken: token, refreshToken: rt }) => {
        try {
          sessionStorage.setItem('ccf_token', token);
          if (rt) {
            sessionStorage.setItem('ccf_refresh_token', rt);
          }
        } catch {
          /* context may be torn down */
        }
      },
      { accessToken, refreshToken },
    );
    const page = await context.newPage();
    try {
      await use(page);
    } finally {
      await page.context().close();
    }
  },

  // Each `*Request` fixture creates a fresh APIRequestContext with Bearer
  // header pre-attached. Built on `pwRequest.newContext` from the
  // playwright test module entry point (this is the documented factory;
  // the `request` fixture is an APIRequestContext, NOT a factory).
  lectorRequest: async (_args, use) => {
    const apiBase = resolveApiBaseUrl();
    test.skip(
      !apiBase || !apiBase.startsWith('http'),
      'Set E2E_API_URL (absolute) so seed-academy-roles + login can run.',
    );
    const { accessToken } = await login('e2e.lector@ccf.local');
    const ctx = await pwRequest.newContext({
      baseURL: apiBase,
      extraHTTPHeaders: {
        Authorization: `Bearer ${accessToken}`,
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
    });
    try {
      await use(ctx);
    } finally {
      await ctx.dispose();
    }
  },
  estudianteRequest: async (_args, use) => {
    const apiBase = resolveApiBaseUrl();
    test.skip(
      !apiBase || !apiBase.startsWith('http'),
      'Set E2E_API_URL (absolute) so seed-academy-roles + login can run.',
    );
    const { accessToken } = await login('e2e.estudiante@ccf.local');
    const ctx = await pwRequest.newContext({
      baseURL: apiBase,
      extraHTTPHeaders: {
        Authorization: `Bearer ${accessToken}`,
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
    });
    try {
      await use(ctx);
    } finally {
      await ctx.dispose();
    }
  },
  maestroRequest: async (_args, use) => {
    const apiBase = resolveApiBaseUrl();
    test.skip(
      !apiBase || !apiBase.startsWith('http'),
      'Set E2E_API_URL (absolute) so seed-academy-roles + login can run.',
    );
    const { accessToken } = await login('e2e.maestro@ccf.local');
    const ctx = await pwRequest.newContext({
      baseURL: apiBase,
      extraHTTPHeaders: {
        Authorization: `Bearer ${accessToken}`,
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
    });
    try {
      await use(ctx);
    } finally {
      await ctx.dispose();
    }
  },
  adminRequest: async (_args, use) => {
    const apiBase = resolveApiBaseUrl();
    test.skip(
      !apiBase || !apiBase.startsWith('http'),
      'Set E2E_API_URL (absolute) so seed-academy-roles + login can run.',
    );
    const { accessToken } = await login('e2e.admin@ccf.local');
    const ctx = await pwRequest.newContext({
      baseURL: apiBase,
      extraHTTPHeaders: {
        Authorization: `Bearer ${accessToken}`,
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
    });
    try {
      await use(ctx);
    } finally {
      await ctx.dispose();
    }
  },
});

export { expect };
