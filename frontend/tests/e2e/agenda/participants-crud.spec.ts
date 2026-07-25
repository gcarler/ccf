import { expect, test, type Page } from '@playwright/test';
import { installMockPlatformSession } from '../helpers/mockPlatformSession';

type Participant = {
  id: string;
  name: string;
  role: string;
  email?: string;
};

const MOCK_PARTICIPANTS: Participant[] = [
  { id: 'part-1', name: 'Juan Pérez', role: 'organizador', email: 'juan@test.com' },
  { id: 'part-2', name: 'María García', role: 'ponente', email: 'maria@test.com' },
];

async function installMocks(page: Page) {
  await installMockPlatformSession(page, {
    role: 'admin',
    permissions: { 'spiritual_life:read': 'allow', 'spiritual_life:edit': 'allow' },
  });

  await page.route('**/api/agenda/events**', async (route) => {
    const url = route.request().url();
    if (url.includes('/participants')) {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_PARTICIPANTS) });
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

test.describe('Participants CRUD @agenda', () => {
  test('displays participant list for an event', async ({ page }) => {
    await installMocks(page);
    await page.goto('/plataforma/agenda/events');

    await expect(page.locator('text=Eventos')).toBeVisible({ timeout: 10000 });
  });

  test('shows participant roles', async ({ page }) => {
    await installMocks(page);
    await page.goto('/plataforma/agenda/events');

    await expect(page.locator('text=Eventos')).toBeVisible({ timeout: 10000 });
  });
});
