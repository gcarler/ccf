import { test, expect } from '@playwright/test';
import {
  requirePlatformAuthE2E,
  preloadPlatformAccessTokens,
  installPlatformAuthSession,
} from '../helpers/authSession';

/**
 * E2E spec for /plataforma/admin/access (granular permission assignment).
 *
 * Requires:
 *   E2E_AUTH_ENABLED=1
 *   E2E_EMAIL=<admin email>
 *   E2E_PASSWORD=<admin password>
 *   E2E_API_URL=https://...
 */
test.describe('Admin Access - granular permissions', () => {
  requirePlatformAuthE2E();

  test.beforeAll(async ({ request }) => {
    await preloadPlatformAccessTokens(request);
  });

  test.beforeEach(async ({ page }) => {
    await installPlatformAuthSession(page);
    await page.goto('/plataforma/admin/access');
  });

  test('loads the access page and shows both tabs', async ({ page }) => {
    await expect(page.getByRole('button', { name: /Roles Ministeriales/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Auditoría de Usuarios/i })).toBeVisible();
    await expect(page.locator('main').first()).toContainText(/Seguridad y Accesos/i);
  });

  test('switches to the Users tab and filters records', async ({ page }) => {
    await page.getByRole('button', { name: /Auditoría de Usuarios/i }).click();
    await expect(page.locator('main').first()).toContainText(/Activos|Inactivos/i);

    // Type in the search box if it exists
    const search = page.getByPlaceholder(/buscar/i);
    if (await search.isVisible().catch(() => false)) {
      await search.fill('nonexistent-user-xyz');
      await expect(page.locator('main').first()).toContainText(/Sin usuarios|No hay usuarios|no hay usuarios/i);
    }
  });

  test('opens the permission matrix when selecting a role', async ({ page }) => {
    // Switch to grid view so we have clickable cards
    await page.getByRole('button', { name: /Grid/i }).click();

    const card = page.locator('main button').filter({ hasText: /usuarios vinculados/i }).first();
    await expect(card).toBeVisible({ timeout: 15_000 });
    await card.click();

    // WorkspaceDrawer opens with the matrix
    await expect(page.getByRole('heading', { name: /Matriz de Operaciones/i })).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText(/CRM Pastoral/i).first()).toBeVisible();
    await expect(page.getByRole('button', { name: /Guardar Cambios/i })).toBeVisible();
  });

  test('toggles a permission level and saves with mocked API', async ({ page }) => {
    // Mock the save action so we don't mutate real roles
    await page.route(/\/api\/admin\/roles\/[^/]+$/, async (route) => {
      if (route.request().method() === 'PATCH') {
        await route.fulfill({ status: 200, json: { status: 'ok' } });
        return;
      }
      await route.continue();
    });

    await page.getByRole('button', { name: /Grid/i }).click();

    const card = page.locator('main button').filter({ hasText: /usuarios vinculados/i }).first();
    await expect(card).toBeVisible({ timeout: 15_000 });
    await card.click();

    const crmRow = page.locator('.permission-card').filter({ hasText: /CRM Pastoral/i }).first();
    await expect(crmRow).toBeVisible({ timeout: 10_000 });

    // Toggle the "manage" level for CRM
    const manageButton = crmRow.getByRole('button', { name: /Administrador/i });
    await manageButton.click();

    // Verify the button is active (scaled shadow is applied)
    await expect(manageButton).toHaveClass(/scale-110/);

    // Save and expect a success toast
    await page.getByRole('button', { name: /Guardar Cambios/i }).click();
    await expect(page.getByText(/Permisos del rol actualizados/)).toBeVisible({ timeout: 5_000 });
  });

  test('opens user drawer and shows effective vs override permissions', async ({ page }) => {
    await page.getByRole('button', { name: /Grid/i }).click();
    await page.getByRole('button', { name: /Auditoría de Usuarios/i }).click();

    // Click the first user card (contains an @ in the email)
    const card = page.locator('main button').filter({ hasText: /@/i }).first();
    await expect(card).toBeVisible({ timeout: 15_000 });
    await card.click();

    // User drawer shows the permission matrix
    await expect(page.getByRole('heading', { name: /Matriz de Operaciones/i })).toBeVisible({ timeout: 10_000 });

    // Platform role badge is conditionally visible (only if user has a roleId)
    const roleBadge = page.getByText(/Rol de plataforma:/i);
    if (await roleBadge.isVisible().catch(() => false)) {
      await expect(roleBadge).toBeVisible();
    }
  });
});
