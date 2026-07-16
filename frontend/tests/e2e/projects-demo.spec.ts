import { expect, test } from '@playwright/test';
import {
  installPlatformAuthSession,
  preloadPlatformAccessTokens,
  requirePlatformAuthE2E,
} from './helpers/authSession';
import { openSeededProjectDetailPath, seedProjectsDemo } from './helpers/projectsDemo';

test.describe('projects demo roundtrip', () => {
  requirePlatformAuthE2E();
  test.setTimeout(60_000);

  test.beforeAll(async ({ request }) => {
    seedProjectsDemo();
    await preloadPlatformAccessTokens(request);
  });

  test.beforeEach(async ({ page }) => {
    await installPlatformAuthSession(page);
  });

  test('muestra los proyectos demo y navega al detalle correcto', async ({ page }) => {
    await page.goto('/plataforma/projects?view=list#projects-list');
    await expect(page.locator('body')).toContainText('Demo Proyecto 1');
    await expect(page.locator('body')).toContainText('Demo Proyecto 2');
    await expect(page.locator('body')).toContainText('Demo Proyecto 3');

    const detailPath = await openSeededProjectDetailPath(page);
    await expect(page.locator('body')).toContainText('Demo Proyecto 1');
    await expect(page.locator('body')).toContainText('Actividad Reciente');
    await expect(page.locator('body')).toContainText('Demo Proyecto 1 · registro demo 5');

    await page.goto(`${detailPath}?view=list`);
    await expect(page.locator('body')).toContainText('Demo Proyecto 1 - Tarea 1: Levantamiento');
    await expect(page.locator('body')).toContainText('Demo Proyecto 1 - Tarea 5: Cierre');
    await expect(page.getByText(/Demo Proyecto 1 - Tarea [1-5]:/)).toHaveCount(5);
    await expect(page.locator('body')).toContainText('Plan de Acción');
  });

  test('la vista de tareas expone las 15 tareas demo', async ({ page }) => {
    await page.goto('/plataforma/projects/tasks?view=list');
    await expect(page.locator('body')).toContainText('Demo Proyecto 1 - Tarea 1: Levantamiento');
    await expect(page.locator('body')).toContainText('Demo Proyecto 2 - Tarea 3: Ejecución');
    await expect(page.locator('body')).toContainText('Demo Proyecto 3 - Tarea 5: Cierre');
    await expect(page.locator('body')).not.toContainText('No hay tareas para este filtro.');
  });
});
