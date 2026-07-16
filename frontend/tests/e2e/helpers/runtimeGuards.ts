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

export async function waitForStableRoute(page: Page, path: string) {
  await page.goto(path, { waitUntil: 'domcontentloaded' });
  await page.waitForLoadState('networkidle', { timeout: 5_000 }).catch(() => {});
  await page.waitForTimeout(750);
}
