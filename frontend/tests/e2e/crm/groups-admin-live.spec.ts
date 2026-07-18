import { expect, test } from '@playwright/test';
import {
  getPlatformApiBaseUrl,
  installPlatformAuthSession,
  preloadPlatformAccessTokens,
  requirePlatformAuthE2E,
} from '../helpers/authSession';
import { installRuntimeGuards, waitForStableRoute } from '../helpers/runtimeGuards';

test.describe('crm groups admin live smoke', () => {
  requirePlatformAuthE2E();
  test.setTimeout(90_000);

  test.beforeAll(async ({ request }) => {
    await preloadPlatformAccessTokens(request);
  });

  test.beforeEach(async ({ page }) => {
    await installPlatformAuthSession(page);
  });

  test('@auth @crm groups admin loads and opens the evangelism bridge without runtime regressions', async ({ page }) => {
    const runtime = installRuntimeGuards(page, getPlatformApiBaseUrl());

    await waitForStableRoute(page, '/plataforma/crm/groups/admin');
    await expect(page.locator('body')).toContainText(/Consola de Grupos|Gestion operativa real de grupos/i, {
      timeout: 20_000,
    });

    const emptyState = page.getByText(/No hay grupos activos para mostrar/i);
    if (await emptyState.isVisible().catch(() => false)) {
      await expect(emptyState).toBeVisible();
    } else {
      const firstGroupCard = page.locator('main section button').filter({ has: page.locator('h4') }).first();
      await expect(firstGroupCard).toBeVisible({ timeout: 10_000 });
      await firstGroupCard.click();

      await expect(page.locator('body')).toContainText(/Reporte Operativo Semanal|Asistencia|Temporada|Enviar Reporte Semanal/i, {
        timeout: 20_000,
      });
    }

    expect(runtime.assetErrors, 'groups admin live smoke should not emit _next/static 4xx/5xx').toEqual([]);
    expect(runtime.apiErrors, 'groups admin live smoke should not emit API 4xx/5xx').toEqual([]);
    expect(runtime.pageErrors, 'groups admin live smoke should not emit page errors').toEqual([]);
    expect(runtime.consoleErrors, 'groups admin live smoke should not emit console.error').toEqual([]);
  });
});
