import { expect, test } from '@playwright/test';
import {
  getPlatformApiBaseUrl,
  installPlatformAuthSession,
  preloadPlatformAccessTokens,
  requirePlatformAuthE2E,
} from '../helpers/authSession';
import { openSeededProjectDetailPath, seedProjectsDemo } from '../helpers/projectsDemo';
import { installRuntimeGuards, waitForStableRoute } from '../helpers/runtimeGuards';

function expectNoUnexpectedApiErrors(apiErrors: string[], route: string) {
  // The shared PlatformShell optionally loads CMS theme/popups. The isolated
  // Projects E2E schema intentionally has no CMS seed, so those two read-only
  // lookups return 404 and use the shell's built-in defaults.
  const unexpectedErrors = apiErrors.filter(
    (error) =>
      !/^404 .*\/api\/cms\/v2\/public\/(?:sites\/ccf\/theme|popups\?site_key=ccf)$/.test(error),
  );
  expect(unexpectedErrors, `${route} should not emit unexpected API 4xx/5xx`).toEqual([]);
}

function expectNoUnexpectedConsoleErrors(consoleErrors: string[], apiErrors: string[], route: string) {
  const optionalCms404s = apiErrors.filter((error) =>
    /^404 .*\/api\/cms\/v2\/public\/(?:sites\/ccf\/theme|popups\?site_key=ccf)$/.test(error),
  ).length;
  const genericResource404s = consoleErrors.filter(
    (error) => error === 'Failed to load resource: the server responded with a status of 404 (Not Found)',
  ).length;
  const unexpectedErrors = consoleErrors.filter(
    (error) => error !== '[API_FAILURE] 404 GET /cms/v2/public/popups: {detail: Site not found}'
      && error !== 'Failed to load resource: the server responded with a status of 404 (Not Found)',
  );

  expect(unexpectedErrors, `${route} should not emit unexpected console errors`).toEqual([]);
  expect(genericResource404s).toBeLessThanOrEqual(optionalCms404s);
}

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
    await expect(page.getByText('Actividad', { exact: true }).first()).toBeVisible({ timeout: 15_000 });
    await expect(page.locator('body')).toContainText(/Nueva Tarea|Pizarra|Fases/i, { timeout: 15_000 });

    const taskTitle = 'Demo Proyecto 1 - Tarea 1: Levantamiento';
    await page.getByRole('button', { name: `Abrir detalle de tarea ${taskTitle}` }).click();
    await expect(page.getByRole('complementary', { name: 'Detalle de tarea' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Cerrar detalle de tarea' })).toBeVisible();
    await page.getByRole('button', { name: 'Cerrar detalle de tarea' }).click();
    await expect(page.getByRole('complementary', { name: 'Detalle de tarea' })).toHaveCount(0);

    await page.getByRole('button', { name: /Presupuesto/ }).first().click();
    const budgetDrawer = page.getByRole('dialog', { name: 'Control Presupuestario y Partidas de Gasto' });
    await expect(budgetDrawer).toBeVisible();
    await expect(budgetDrawer.getByText('Estado de Fondos')).toBeVisible();
    await budgetDrawer.getByRole('button', { name: 'Cerrar panel' }).click();
    await expect(budgetDrawer).toHaveCount(0);

    const settingsTrigger = page.getByRole('button', { name: 'Editar', exact: true });
    await settingsTrigger.click();
    const settingsDrawer = page.getByRole('dialog', { name: 'Editar proyecto' });
    await expect(settingsDrawer).toBeVisible();
    const closeSettingsButton = settingsDrawer.getByRole('button', { name: 'Cerrar panel' });
    const saveSettingsButton = settingsDrawer.getByRole('button', { name: 'Guardar Cambios' });
    await expect(closeSettingsButton).toBeFocused();
    await page.keyboard.press('Shift+Tab');
    await expect(saveSettingsButton).toBeFocused();
    await page.keyboard.press('Escape');
    await expect(settingsDrawer).toHaveCount(0);
    await expect(settingsTrigger).toBeFocused();

    expect(runtime.assetErrors, `${detailPath} should not emit _next/static 4xx/5xx`).toEqual([]);
    expectNoUnexpectedApiErrors(runtime.apiErrors, detailPath);
    expect(runtime.pageErrors, `${detailPath} should not emit page errors`).toEqual([]);
    expectNoUnexpectedConsoleErrors(runtime.consoleErrors, runtime.apiErrors, detailPath);
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
    expectNoUnexpectedApiErrors(runtime.apiErrors, listPath);
    expect(runtime.pageErrors, `${listPath} should not emit page errors`).toEqual([]);
    expectNoUnexpectedConsoleErrors(runtime.consoleErrors, runtime.apiErrors, listPath);
  });

  test('@auth @projects-detail calendar view stays stable on seeded detail', async ({ page }) => {
    const runtime = installRuntimeGuards(page, getPlatformApiBaseUrl());
    const detailPath = await openSeededProjectDetailPath(page);
    const calendarPath = `${detailPath}?view=calendar`;

    await waitForStableRoute(page, calendarPath);
    await expect(page.locator('body')).toContainText(/Calendario: Demo Proyecto 1|Demo Proyecto 1/i, { timeout: 15_000 });
    await expect(page.locator('body')).toContainText(/Demo Proyecto 1 - Tarea 1: Levantamiento|Demo Proyecto 1 - Tarea 5: Cierre/i, { timeout: 15_000 });

    expect(runtime.assetErrors, `${calendarPath} should not emit _next/static 4xx/5xx`).toEqual([]);
    expectNoUnexpectedApiErrors(runtime.apiErrors, calendarPath);
    expect(runtime.pageErrors, `${calendarPath} should not emit page errors`).toEqual([]);
    expectNoUnexpectedConsoleErrors(runtime.consoleErrors, runtime.apiErrors, calendarPath);
  });

  test('@auth @projects-detail Gantt selector exposes every dependency type and cancel does not submit', async ({ page }) => {
    const runtime = installRuntimeGuards(page, getPlatformApiBaseUrl());
    const detailPath = await openSeededProjectDetailPath(page);
    const ganttPath = `${detailPath}?view=gantt`;

    await waitForStableRoute(page, ganttPath);
    await expect(page.getByRole('heading', { name: 'Gantt PRO & Cronograma' })).toBeVisible({ timeout: 15_000 });
    await expect(page.locator('body')).toContainText(/Demo Proyecto 1 - Tarea 1: Levantamiento/i);

    await page.getByRole('button', { name: 'Conectar dependencia' }).click();
    const dependencyDrawer = page.getByRole('dialog', { name: 'Vincular dependencia entre tareas' });
    await expect(dependencyDrawer).toBeVisible();
    const dependencyType = dependencyDrawer.getByLabel('Tipo de Enlace');
    for (const type of ['FS', 'SS', 'FF', 'SF']) {
      await dependencyType.selectOption(type);
      await expect(dependencyType).toHaveValue(type);
    }
    await dependencyDrawer.getByRole('button', { name: /Cancelar/i }).click();
    await expect(dependencyDrawer).toHaveCount(0);

    expect(runtime.assetErrors, `${ganttPath} should not emit _next/static 4xx/5xx`).toEqual([]);
    expectNoUnexpectedApiErrors(runtime.apiErrors, ganttPath);
    expect(runtime.pageErrors, `${ganttPath} should not emit page errors`).toEqual([]);
    expectNoUnexpectedConsoleErrors(runtime.consoleErrors, runtime.apiErrors, ganttPath);
  });

  test('@auth @projects-rbac project deletion action matches the authenticated permission', async ({ page }) => {
    const runtime = installRuntimeGuards(page, getPlatformApiBaseUrl());
    const detailPath = await openSeededProjectDetailPath(page);

    await expect(page.getByRole('button', { name: 'Eliminar', exact: true })).toBeVisible();

    expectNoUnexpectedApiErrors(runtime.apiErrors, detailPath);
    expect(runtime.pageErrors, `${detailPath} should not emit page errors`).toEqual([]);
  });
});
