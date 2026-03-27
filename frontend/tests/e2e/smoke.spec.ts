import { expect, test } from '@playwright/test';

test('login page renders', async ({ page }) => {
  await page.goto('/login');
  await expect(page).toHaveTitle(/CCF|Login|Platform/i);
});

test('faro public page loads', async ({ page }) => {
  await page.goto('/faro');
  await expect(page.locator('body')).toContainText(/faro|comunidad|ccf/i);
});
