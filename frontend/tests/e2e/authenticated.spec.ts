import { expect, test } from '@playwright/test';

const email = process.env.E2E_EMAIL || '';
const password = process.env.E2E_PASSWORD || '';
const apiUrl = process.env.NEXT_PUBLIC_API_URL || process.env.E2E_API_URL || '';
const authE2eEnabled = process.env.E2E_AUTH_ENABLED === '1';
const expectEvangelismRestricted = process.env.E2E_EXPECT_EVANGELISM_RESTRICTED === '1';

test.describe('authenticated routes', () => {
  test.skip(
    !authE2eEnabled || !email || !password || !apiUrl,
    'Set E2E_AUTH_ENABLED=1, E2E_EMAIL, E2E_PASSWORD and E2E_API_URL/NEXT_PUBLIC_API_URL.'
  );
  test.setTimeout(45_000);
  test.beforeAll(async ({ request }) => {
    if (!apiUrl.startsWith('http')) {
      test.skip(true, 'Use E2E_API_URL/NEXT_PUBLIC_API_URL absoluto para validar login previo.');
      return;
    }
    try {
      const response = await request.post(`${apiUrl.replace(/\/$/, '')}/auth/login`, {
        form: { username: email, password },
        timeout: 10_000,
      });
      test.skip(!response.ok(), `Preflight login failed against ${apiUrl}/auth/login`);
    } catch {
      test.skip(true, `Preflight login timeout/unreachable at ${apiUrl}/auth/login`);
    }
  });

  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.locator('input[type="text"]').first().fill(email);
    await page.locator('input[type="password"]').first().fill(password);
    await page.locator('button[type="submit"]').first().click();
    await expect(page).not.toHaveURL(/\/login(?:\?|$)/i);
  });

  test('@auth academy route loads for authenticated user', async ({ page }) => {
    await page.goto('/academy');
    await expect(page.locator('body')).toContainText(/academia|curso|coach|faro/i);
  });

  test('@auth projects route loads for authenticated user', async ({ page }) => {
    await page.goto('/projects');
    await expect(page.locator('body')).toContainText(/proyectos|tasks|pipeline|kanban/i);
  });

  test('@auth crm route loads for authenticated user', async ({ page }) => {
    await page.goto('/crm');
    await expect(page.locator('body')).toContainText(/crm|pastoral|pipeline|miembros/i);
  });

  test('@auth crm pipeline route loads for authenticated user', async ({ page }) => {
    await page.goto('/crm/pipeline');
    await expect(page.locator('body')).toContainText(/pipeline|consolidaci[oó]n|lead/i);
  });

  test('@auth new groups and theme routes load for authenticated user', async ({ page }) => {
    await page.goto('/groups/map');
    await expect(page.locator('body')).toContainText(/mapa|coordenadas|casas/i);

    await page.goto('/groups/analytics');
    await expect(page.locator('body')).toContainText(/analitica|top grupos|ocupacion/i);

    await page.goto('/groups/history');
    await expect(page.locator('body')).toContainText(/historial|meses|registros/i);

    await page.goto('/theme');
    await expect(page.locator('body')).toContainText(/tema visual|modo|personalizacion/i);
  });

  test('@auth evangelism events enforces restricted access for non pastoral/admin roles', async ({ page }) => {
    test.skip(!expectEvangelismRestricted, 'Set E2E_EXPECT_EVANGELISM_RESTRICTED=1 for non pastoral/admin users.');
    await page.goto('/evangelism/events');
    await expect(page.locator('body')).toContainText(/acceso restringido|requiere rol pastoral o administrativo/i);
  });
});
