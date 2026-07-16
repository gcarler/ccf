import { expect, test } from '@playwright/test';
import {
  getPlatformApiBaseUrl,
  installPlatformAuthSession,
  preloadPlatformAccessTokens,
  requirePlatformAuthE2E,
} from '../helpers/authSession';
import { openSeededProjectDetailPath, seedProjectsDemo } from '../helpers/projectsDemo';
import { installRuntimeGuards, waitForStableRoute } from '../helpers/runtimeGuards';

test.describe('projects detail seeded smoke', () => {
  requirePlatformAuthE2E();
  test.setTimeout(60_000);

  test.beforeAll(async ({ request }) => {
    seedProjectsDemo();
    await preloadPlatformAccessTokens(request);
  });

  test.beforeEach(async ({ page }) => {
    await installPlatformAuthSession(page);
  });

  test('@auth @projects-detail dashboard view stays stable on seeded detail', async ({ page }) => {
    const runtime = installRuntimeGuards(page, getPlatformApiBaseUrl());
    const detailPath = await openSeededProjectDetailPath(page);

    await expect(page.locator('body')).toContainText(/Demo Proyecto 1/i, { timeout: 15_000 });
    await expect(page.locator('body')).toContainText(/Actividad Reciente|Pulso del Equipo/i, { timeout: 15_000 });
    await expect(page.locator('body')).toContainText(/Nueva Tarea|Pizarra|Fases/i, { timeout: 15_000 });

    expect(runtime.assetErrors, `${detailPath} should not emit _next/static 4xx/5xx`).toEqual([]);
    expect(runtime.apiErrors, `${detailPath} should not emit API 4xx/5xx`).toEqual([]);
    expect(runtime.pageErrors, `${detailPath} should not emit page errors`).toEqual([]);
    expect(runtime.consoleErrors, `${detailPath} should not emit console.error`).toEqual([]);
  });

  test('@auth @projects-detail list view keeps seeded task set stable', async ({ page }) => {
    const runtime = installRuntimeGuards(page, getPlatformApiBaseUrl());
    const detailPath = await openSeededProjectDetailPath(page);
    const listPath = `${detailPath}?view=list`;

    await waitForStableRoute(page, listPath);
    await expect(page.locator('body')).toContainText('Demo Proyecto 1 - Tarea 1: Levantamiento', { timeout: 15_000 });
    await expect(page.locator('body')).toContainText('Demo Proyecto 1 - Tarea 5: Cierre', { timeout: 15_000 });
    await expect(page.locator('body')).toContainText(/Plan de Acción/i, { timeout: 15_000 });

    expect(runtime.assetErrors, `${listPath} should not emit _next/static 4xx/5xx`).toEqual([]);
    expect(runtime.apiErrors, `${listPath} should not emit API 4xx/5xx`).toEqual([]);
    expect(runtime.pageErrors, `${listPath} should not emit page errors`).toEqual([]);
    expect(runtime.consoleErrors, `${listPath} should not emit console.error`).toEqual([]);
  });

  test('@auth @projects-detail calendar view stays stable on seeded detail', async ({ page }) => {
    const runtime = installRuntimeGuards(page, getPlatformApiBaseUrl());
    const detailPath = await openSeededProjectDetailPath(page);
    const calendarPath = `${detailPath}?view=calendar`;

    await waitForStableRoute(page, calendarPath);
    await expect(page.locator('body')).toContainText(/Calendario: Demo Proyecto 1|Demo Proyecto 1/i, { timeout: 15_000 });
    await expect(page.locator('body')).toContainText(/Demo Proyecto 1 - Tarea 1: Levantamiento|Demo Proyecto 1 - Tarea 5: Cierre/i, { timeout: 15_000 });

    expect(runtime.assetErrors, `${calendarPath} should not emit _next/static 4xx/5xx`).toEqual([]);
    expect(runtime.apiErrors, `${calendarPath} should not emit API 4xx/5xx`).toEqual([]);
    expect(runtime.pageErrors, `${calendarPath} should not emit page errors`).toEqual([]);
    expect(runtime.consoleErrors, `${calendarPath} should not emit console.error`).toEqual([]);
  });
});
