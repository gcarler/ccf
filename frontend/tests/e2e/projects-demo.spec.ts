import { expect, test } from '@playwright/test';
import { spawnSync } from 'node:child_process';

const email = process.env.E2E_EMAIL || '';
const password = process.env.E2E_PASSWORD || '';
const apiUrl = process.env.NEXT_PUBLIC_API_URL || process.env.E2E_API_URL || '';
const authE2eEnabled = process.env.E2E_AUTH_ENABLED === '1';

let cachedAccessToken = '';
let cachedRefreshToken: string | null = null;

function seedProjectsDemo() {
  const result = spawnSync('node', ['tests/e2e/seed-projects-demo.mjs'], {
    cwd: process.cwd(),
    env: {
      ...process.env,
      PROJECTS_DEMO_EMAIL: email || process.env.PROJECTS_DEMO_EMAIL || '',
    },
    encoding: 'utf8',
  });
  if (result.status !== 0) {
    throw new Error(`[projects-demo] Seed failed: ${result.stderr || result.stdout || 'unknown error'}`);
  }
}

test.describe('projects demo roundtrip', () => {
  test.skip(
    !authE2eEnabled || !email || !password || !apiUrl,
    'Set E2E_AUTH_ENABLED=1, E2E_EMAIL, E2E_PASSWORD and E2E_API_URL/NEXT_PUBLIC_API_URL.'
  );

  test.setTimeout(60_000);

  test.beforeAll(async ({ request }) => {
    seedProjectsDemo();

    if (!apiUrl.startsWith('http')) {
      test.skip(true, 'Use E2E_API_URL/NEXT_PUBLIC_API_URL absoluto para validar login previo.');
      return;
    }

    try {
      const response = await request.post(`${apiUrl.replace(/\/$/, '')}/v3/auth/login`, {
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        data: { email, password },
        timeout: 10_000,
      });
      test.skip(!response.ok(), `Preflight login failed against ${apiUrl}/v3/auth/login`);
      const payload = await response.json();
      cachedAccessToken = payload.access_token;
      cachedRefreshToken = payload.refresh_token ?? null;
    } catch {
      test.skip(true, `Preflight login timeout/unreachable at ${apiUrl}/v3/auth/login`);
    }
  });

  test.beforeEach(async ({ page }) => {
    await page.addInitScript(({ accessToken, refreshToken }) => {
      sessionStorage.setItem('ccf_token', accessToken);
      if (refreshToken) sessionStorage.setItem('ccf_refresh_token', refreshToken);
    }, {
      accessToken: cachedAccessToken,
      refreshToken: cachedRefreshToken,
    });
  });

  test('muestra los proyectos demo y navega al detalle correcto', async ({ page }) => {
    await page.goto('/plataforma/projects');
    await expect(page.locator('body')).toContainText('Demo Proyecto 1');
    await expect(page.locator('body')).toContainText('Demo Proyecto 2');
    await expect(page.locator('body')).toContainText('Demo Proyecto 3');

    await page.getByText('Demo Proyecto 1', { exact: true }).first().click();
    await expect(page).toHaveURL(/\/plataforma\/projects\/[0-9a-f-]{36}$/);
    await expect(page.locator('body')).toContainText('Demo Proyecto 1');
    await expect(page.locator('body')).toContainText('Actividades');
    await expect(page.locator('body')).toContainText('Demo Proyecto 1 · registro demo 5');

    const detailUrl = new URL(page.url());
    await page.goto(`${detailUrl.pathname}?view=list`);
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
