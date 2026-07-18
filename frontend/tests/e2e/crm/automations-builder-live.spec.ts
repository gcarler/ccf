import { expect, test } from '@playwright/test';
import {
  getPlatformApiBaseUrl,
  installPlatformAuthSession,
  preloadPlatformAccessTokens,
  requirePlatformAuthE2E,
} from '../helpers/authSession';
import { installRuntimeGuards, waitForStableRoute } from '../helpers/runtimeGuards';

test.describe('crm automations builder live smoke', () => {
  requirePlatformAuthE2E();
  test.setTimeout(90_000);

  test.beforeAll(async ({ request }) => {
    await preloadPlatformAccessTokens(request);
  });

  test.beforeEach(async ({ page }) => {
    await installPlatformAuthSession(page);
  });

  test('@auth @crm automations builder loads without runtime regressions', async ({ page }) => {
    const runtime = installRuntimeGuards(page, getPlatformApiBaseUrl());

    await waitForStableRoute(page, '/plataforma/crm/settings/automations/builder');
    await expect(page.locator('body')).toContainText(/Constructor Visual|Propiedades del Elemento|Añadir Paso|Guardar Flujo/i, {
      timeout: 20_000,
    });

    await expect(page.getByRole('button', { name: /Guardar Flujo/i })).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('body')).toContainText(/Propiedades del Elemento|Selecciona un paso o una línea de conexión/i, {
      timeout: 10_000,
    });

    expect(runtime.assetErrors, 'automations builder live smoke should not emit _next/static 4xx/5xx').toEqual([]);
    expect(runtime.apiErrors, 'automations builder live smoke should not emit API 4xx/5xx').toEqual([]);
    expect(runtime.pageErrors, 'automations builder live smoke should not emit page errors').toEqual([]);
    expect(runtime.consoleErrors, 'automations builder live smoke should not emit console.error').toEqual([]);
  });
});
