import { expect, test, type Page } from '@playwright/test';
import { installMockPlatformSession } from '../helpers/mockPlatformSession';

type Reservation = {
  id: string;
  resourceId: string;
  resourceName: string;
  startsAt: string;
  endsAt: string;
};

const MOCK_RESERVATIONS: Reservation[] = [
  {
    id: 'res-1',
    resourceId: 'r-1',
    resourceName: 'Sala de conferencias',
    startsAt: '2026-07-28T10:00:00.000Z',
    endsAt: '2026-07-28T12:00:00.000Z',
  },
];

async function installMocks(page: Page) {
  await installMockPlatformSession(page, {
    role: 'admin',
    permissions: { 'spiritual_life:read': 'allow', 'spiritual_life:edit': 'allow' },
  });

  await page.route('**/api/agenda/events**', async (route) => {
    const url = route.request().url();
    if (url.includes('/reservations')) {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_RESERVATIONS) });
    } else {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    }
  });

  await page.route('**/api/system/calendar**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });

  await page.route('**/api/projects/_tasks**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ _tasks: [] }) });
  });
}

test.describe('Reservations CRUD @agenda', () => {
  test('displays reservation in calendar', async ({ page }) => {
    await installMocks(page);
    await page.goto('/plataforma/calendar');

    await expect(page.locator('text=Sala de conferencias')).toBeVisible({ timeout: 10000 });
  });

  test('shows reservation time range', async ({ page }) => {
    await installMocks(page);
    await page.goto('/plataforma/calendar');

    await expect(page.locator('text=10:00')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=12:00')).toBeVisible();
  });
});
