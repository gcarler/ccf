import { expect, test } from '@playwright/test';

const email = process.env.E2E_EMAIL || '';
const password = process.env.E2E_PASSWORD || '';
const apiUrl = process.env.NEXT_PUBLIC_API_URL || process.env.E2E_API_URL || '';

test.describe('authenticated routes', () => {
  test.skip(!email || !password || !apiUrl, 'Set E2E_EMAIL, E2E_PASSWORD and E2E_API_URL/NEXT_PUBLIC_API_URL.');

  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.getByPlaceholder(/correo@ejemplo.com/i).fill(email);
    await page.locator('input[type="password"]').first().fill(password);
    await page.getByRole('button', { name: /iniciar sesi/i }).click();
    await page.waitForLoadState('networkidle');
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
});
