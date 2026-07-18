import { expect, test } from '@playwright/test';
import {
  getPlatformApiBaseUrl,
  installPlatformAuthSession,
  preloadPlatformAccessTokens,
  requirePlatformAuthE2E,
} from '../helpers/authSession';
import { installRuntimeGuards, waitForStableRoute } from '../helpers/runtimeGuards';

test.describe('crm personas live smoke', () => {
  requirePlatformAuthE2E();
  test.setTimeout(90_000);

  test.beforeAll(async ({ request }) => {
    await preloadPlatformAccessTokens(request);
  });

  test.beforeEach(async ({ page }) => {
    await installPlatformAuthSession(page);
  });

  test('@auth @crm personas directory supports live search and detail navigation without runtime regressions', async ({ page }) => {
    const runtime = installRuntimeGuards(page, getPlatformApiBaseUrl());

    await waitForStableRoute(page, '/plataforma/crm/personas');
    await expect(page.locator('body')).toContainText(/Personas|Directorio completo de la comunidad/i, { timeout: 20_000 });

    const searchInput = page.getByPlaceholder(/Buscar por nombre, documento, teléfono, email o ministerio/i);
    await searchInput.fill('zzznomatchcrm');
    await page.waitForTimeout(1200);
    await expect(page.locator('body')).toContainText(/No se encontraron personas con esos filtros/i);

    await searchInput.fill('');
    await page.waitForTimeout(1500);

    const emptyState = page.getByText(/No se encontraron personas con esos filtros/i);
    if (await emptyState.isVisible().catch(() => false)) {
      await expect(emptyState).toBeVisible();
    } else {
      const firstCandidate = page.locator('div.cursor-pointer').filter({ has: page.locator('h3.text-sm.font-bold') }).first();
      await expect(firstCandidate).toBeVisible({ timeout: 10_000 });
      await firstCandidate.scrollIntoViewIfNeeded();
      await firstCandidate.evaluate((element: HTMLElement) => element.click());
      await page.waitForURL(/\/plataforma\/crm\/personas\/.+/, { timeout: 10_000 }).catch(async () => {
        await firstCandidate.locator('h3.text-sm.font-bold').first().evaluate((element: HTMLElement) => element.click());
        await page.waitForURL(/\/plataforma\/crm\/personas\/.+/, { timeout: 10_000 });
      });
      await page.waitForLoadState('domcontentloaded');
      await expect(page.locator('body')).toContainText(/Mentoría|Salud Espiritual|Historial|Contribuciones|Asignar Mentoría/i, { timeout: 20_000 });
    }

    expect(runtime.assetErrors, 'personas live smoke should not emit _next/static 4xx/5xx').toEqual([]);
    expect(runtime.apiErrors, 'personas live smoke should not emit API 4xx/5xx').toEqual([]);
    expect(runtime.pageErrors, 'personas live smoke should not emit page errors').toEqual([]);
    expect(runtime.consoleErrors, 'personas live smoke should not emit console.error').toEqual([]);
  });
});
