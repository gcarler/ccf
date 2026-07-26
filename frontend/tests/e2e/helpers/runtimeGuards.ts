import type { Page } from '@playwright/test';

export type RuntimeGuards = {
  consoleErrors: string[];
  pageErrors: string[];
  assetErrors: string[];
  apiErrors: string[];
};

export function installRuntimeGuards(page: Page, apiBaseUrl?: string): RuntimeGuards {
  const consoleErrors: string[] = [];
  const pageErrors: string[] = [];
  const assetErrors: string[] = [];
  const apiErrors: string[] = [];

  page.on('console', (message) => {
    if (message.type() === 'error') {
      consoleErrors.push(message.text());
    }
  });

  page.on('pageerror', (error) => {
    pageErrors.push(error.message);
  });

  page.on('response', (response) => {
    const url = response.url();
    const status = response.status();
    if (status < 400) return;

    if (url.includes('/_next/static/')) {
      assetErrors.push(`${status} ${url}`);
      return;
    }

    if (url.includes('/api/') || (apiBaseUrl && url.startsWith(apiBaseUrl))) {
      apiErrors.push(`${status} ${url}`);
    }
  });

  return { consoleErrors, pageErrors, assetErrors, apiErrors };
}

/**
 * Navigates to a route and waits for it to become stable.
 * 
 * For authenticated routes the SPA may show a brief splash/loading state
 * while the AuthContext bootstraps and data fetches complete. This helper
 * waits for network idle, then for the CCF brand splash to disappear,
 * then for a short render budget so elements settle before assertions.
 */
export async function waitForStableRoute(page: Page, path: string) {
  await page.goto(path, { waitUntil: 'domcontentloaded' });
  // Wait for the initial RSC payload + auth/me + page data calls to complete.
  await page.waitForLoadState('networkidle', { timeout: 5_000 }).catch(() => {});
  // Give React hydration + re-render time after network settles.
  await page.waitForTimeout(750);
  // If the CCF brand splash is still visible, wait for it to disappear.
  await page.locator('text=CCF').waitFor({ state: 'hidden', timeout: 10_000 })
    .catch(() => {});
}
