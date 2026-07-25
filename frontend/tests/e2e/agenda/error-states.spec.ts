import { expect, test, type Page } from '@playwright/test';
import { installMockPlatformSession } from '../helpers/mockPlatformSession';

async function installErrorMocks(page: Page) {
  await installMockPlatformSession(page, {
    role: 'admin',
    permissions: { 'spiritual_life:read': 'allow', 'spiritual_life:edit': 'allow' },
  });

  await page.route('**/api/system/calendar**', async (route) => {
    await route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'Internal error' }) });
  });

  await page.route('**/api/projects/_tasks**', async (route) => {
    await route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'Internal error' }) });
  });
}

test.describe('Error states @agenda', () => {
  test('shows error message when calendar API fails', async ({ page }) => {
    await installErrorMocks(page);
    await page.goto('/plataforma/calendar');

    await expect(page.locator('text=No se pudieron cargar los datos del calendario.')).toBeVisible({ timeout: 10000 });
  });

  test('shows retry button on error', async ({ page }) => {
    await installErrorMocks(page);
    await page.goto('/plataforma/calendar');

    const retryBtn = page.locator('button:has-text("Reintentar")');
    await expect(retryBtn).toBeVisible({ timeout: 10000 });
  });

  test('retry button attempts to reload data', async ({ page }) => {
    let callCount = 0;
    await installMockPlatformSession(page, {
      role: 'admin',
      permissions: { 'spiritual_life:read': 'allow', 'spiritual_life:edit': 'allow' },
    });

    await page.route('**/api/system/calendar**', async (route) => {
      callCount++;
      if (callCount === 1) {
        await route.fulfill({ status: 500, contentType: 'application/json', body: '{}' });
      } else {
        await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
      }
    });

    await page.route('**/api/projects/_tasks**', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ _tasks: [] }) });
    });

    await page.goto('/plataforma/calendar');
    await expect(page.locator('button:has-text("Reintentar")')).toBeVisible({ timeout: 10000 });

    await page.click('button:has-text("Reintentar")');
    await expect(page.locator('text=Calendario')).toBeVisible({ timeout: 10000 });
    expect(callCount).toBeGreaterThanOrEqual(2);
  });
});
