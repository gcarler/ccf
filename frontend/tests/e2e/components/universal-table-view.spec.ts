/**
 * UniversalTableView real AG Grid integration spec.
 * Requires the same E2E auth env vars as other platform E2E specs
 * (E2E_AUTH_ENABLED=1, E2E_EMAIL, E2E_PASSWORD, E2E_API_URL/NEXT_PUBLIC_API_URL).
 */
import { expect, test } from '@playwright/test';
import {
  installPlatformAuthSession,
  preloadPlatformAccessTokens,
  requirePlatformAuthE2E,
} from '../helpers/authSession';
import { seedProjectsDemo } from '../helpers/projectsDemo';

test.describe('UniversalTableView real AG Grid integration', () => {
  requirePlatformAuthE2E();
  test.setTimeout(60_000);

  test.beforeAll(async ({ request }) => {
    seedProjectsDemo();
    await preloadPlatformAccessTokens(request);
  });

  test.beforeEach(async ({ page }) => {
    await installPlatformAuthSession(page);
    await page.goto('/plataforma/tasks');
    await page.getByTitle('Tabla').click();
    await expect(page.locator('.ag-root-wrapper')).toBeVisible({ timeout: 10_000 });
  });

  test('renders real AG Grid rows with seeded tasks', async ({ page }) => {
    await expect(page.locator('.ag-header-cell[col-id="title"]')).toContainText('Tarea');
    await expect(page.locator('.ag-header-cell[col-id="project_title"]')).toContainText('Proyecto');
    await expect(page.locator('.ag-header-cell[col-id="priority"]')).toContainText('Prioridad');
    await expect(page.locator('.ag-header-cell[col-id="status"]')).toContainText('Estado');

    await expect(page.locator('.ag-row:not(.ag-hidden)').first()).toBeVisible();
    await expect(page.locator('.ag-body-viewport')).toContainText('Demo Proyecto 1');
  });

  test('groups rows by status using real AG Grid groups', async ({ page }) => {
    await expect(page.locator('.ag-full-width-row').first()).toBeVisible();
  });

  test('filters rows via the quick search input', async ({ page }) => {
    const search = page.getByPlaceholder('Buscar…');
    await search.fill('Tarea 1: Levantamiento');

    await expect(
      page.locator('.ag-row:not(.ag-hidden)').filter({ hasText: 'Tarea 1: Levantamiento' })
    ).toBeVisible();
    await expect(
      page.locator('.ag-row:not(.ag-hidden)').filter({ hasText: 'Tarea 5: Cierre' })
    ).toHaveCount(0);
  });

  test('sorts rows when clicking a column header', async ({ page }) => {
    const priorityHeader = page.locator('.ag-header-cell[col-id="priority"]');

    await priorityHeader.click();
    await expect(priorityHeader).toHaveAttribute('aria-sort', 'ascending');

    await priorityHeader.click();
    await expect(priorityHeader).toHaveAttribute('aria-sort', 'descending');
  });

  test('opens task detail drawer when clicking a row', async ({ page }) => {
    const titleCell = page
      .locator('.ag-row:not(.ag-hidden) [col-id="title"]')
      .filter({ hasText: 'Demo Proyecto 1 - Tarea 1' })
      .first();
    await titleCell.click();

    // The drawer is a fixed <aside> that contains the MESH AI section
    const drawer = page.locator('aside').filter({ hasText: 'MESH AI' });
    await expect(drawer).toBeVisible();
  });
});
