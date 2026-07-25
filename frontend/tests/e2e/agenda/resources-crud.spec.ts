import { expect, test, type Page } from '@playwright/test';
import { installMockPlatformSession } from '../helpers/mockPlatformSession';

type Resource = {
  id: string;
  name: string;
  type: string;
  capacity?: number;
  location?: string;
};

const MOCK_RESOURCES: Resource[] = [
  { id: 'res-1', name: 'Sala de conferencias', type: 'sala', capacity: 30, location: 'Piso 2' },
  { id: 'res-2', name: 'Proyector portátil', type: 'equipo', capacity: 0, location: 'Almacén' },
];

async function installMocks(page: Page) {
  await installMockPlatformSession(page, {
    role: 'admin',
    permissions: { 'spiritual_life:read': 'allow', 'spiritual_life:edit': 'allow' },
  });

  await page.route('**/api/agenda/resources**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_RESOURCES) });
  });

  await page.route('**/api/system/calendar**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });

  await page.route('**/api/projects/_tasks**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ _tasks: [] }) });
  });
}

test.describe('Resources CRUD @agenda', () => {
  test('displays resource list in sidebar', async ({ page }) => {
    await installMocks(page);
    await page.goto('/plataforma/calendar');

    await expect(page.locator('text=Recursos')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=Sala de conferencias')).toBeVisible();
    await expect(page.locator('text=Proyector portátil')).toBeVisible();
  });

  test('shows resource type and location', async ({ page }) => {
    await installMocks(page);
    await page.goto('/plataforma/calendar');

    await expect(page.locator('text=Piso 2')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=Almacén')).toBeVisible();
  });
});
