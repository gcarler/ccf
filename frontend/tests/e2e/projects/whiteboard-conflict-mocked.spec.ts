import { expect, test } from '@playwright/test';
import { waitForStableRoute } from '../helpers/runtimeGuards';

const projectId = '00000000-0000-4000-8000-000000000061';
const initialVersion = '2026-10-05T10:00:00+00:00';
const serverVersion = '2026-10-05T10:01:00+00:00';

test('Projects preserves local whiteboard edits after a stale-version conflict', async ({ page }) => {
  const project = {
    id: projectId,
    title: 'Proyecto Pizarra Concurrencia',
    description: 'Fixture de conflicto concurrente sin base de datos.',
    status: 'active',
    color: null,
    owner_id: null,
    progress_percent: 0,
    tasks: [],
    milestones: [],
    created_at: initialVersion,
    updated_at: initialVersion,
  };
  const saves: Record<string, unknown>[] = [];
  const pageErrors: string[] = [];
  page.on('pageerror', (error) => pageErrors.push(error.message));
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.routeWebSocket(`**/api/projects/${projectId}/whiteboard/ws**`, (socket) => {
    socket.onMessage(() => undefined);
  });
  await page.route('**/api/**', async (route) => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname;
    if (request.method() === 'POST' && pathname === `/api/projects/${projectId}/whiteboard`) {
      saves.push(request.postDataJSON() as Record<string, unknown>);
      await route.fulfill({
        status: 409,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: {
            code: 'whiteboard_conflict',
            message: 'La pizarra fue modificada en otra sesión.',
            current_updated_at: serverVersion,
          },
        }),
      });
      return;
    }
    if (request.method() !== 'GET') {
      await route.fulfill({ status: 405, body: 'Unexpected mutation blocked by E2E' });
      return;
    }

    let body: unknown = [];
    if (pathname.endsWith('/v3/auth/me')) {
      body = {
        auth_user_id: 'projects-whiteboard-conflict-e2e',
        username: 'projects.whiteboard.e2e',
        email: 'projects.whiteboard.e2e@ccf.local',
        platform_role: 'GESTOR',
        is_verified: true,
        permissions: { 'projects:read': 'allow', 'projects:edit': 'allow' },
      };
    } else if (pathname === `/api/projects/${projectId}`) {
      body = project;
    } else if (pathname === `/api/projects/${projectId}/tasks` || pathname === '/api/projects/activities') {
      body = [];
    } else if (pathname === `/api/projects/${projectId}/phases`) {
      body = [];
    } else if (pathname === `/api/projects/${projectId}/whiteboard`) {
      body = {
        id: 'whiteboard-e2e-1',
        project_id: projectId,
        title: 'Pizarra de concurrencia',
        elements_json: JSON.stringify({ version: '6.0.0', objects: [] }),
        created_at: initialVersion,
        updated_at: initialVersion,
      };
    }

    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
  });
  await page.addInitScript(() => {
    sessionStorage.setItem('ccf_token', 'projects-whiteboard-conflict-e2e-token');
    sessionStorage.setItem('ccf_refresh_token', 'projects-whiteboard-conflict-e2e-refresh');
  });

  const authLoaded = page.waitForResponse((response) => (
    response.url().includes('/api/v3/auth/me') && response.request().method() === 'GET'
  ));
  await waitForStableRoute(page, `/plataforma/projects/${projectId}?view=gantt`);
  await authLoaded;
  const boardLoaded = page.waitForResponse((response) => (
    response.url().includes(`/api/projects/${projectId}/whiteboard`)
    && response.request().method() === 'GET'
  ));
  await page.getByRole('button', { name: 'Pizarra', exact: true }).click();
  await boardLoaded;
  await page.locator('canvas.whiteboard-canvas').first().waitFor({ state: 'visible' });
  const conflictResponse = page.waitForResponse((response) => (
    response.url().includes(`/api/projects/${projectId}/whiteboard`)
    && response.request().method() === 'POST'
  ));
  const startBlank = page.getByRole('button', { name: 'Iniciar con pizarra en blanco' });
  if (await startBlank.isVisible().catch(() => false)) {
    await startBlank.click();
  } else {
    await page.getByTestId('whiteboard-add-text').click();
  }
  expect((await conflictResponse).status()).toBe(409);

  await expect(page.getByText(/versión más reciente|versión guardada cambió/i)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Guardar' })).toBeDisabled();
  expect(saves).toHaveLength(1);
  expect(saves[0]).toMatchObject({ base_updated_at: initialVersion });
  await page.getByRole('button', { name: 'Cerrar pizarra' }).click();
  const closePanel = page.getByRole('dialog', { name: 'Cerrar pizarra' });
  await expect(closePanel).toContainText('expórtalos antes de cerrar y volver a cargar');
  await expect(closePanel.getByRole('button', { name: 'Recarga para guardar' })).toBeDisabled();
  await closePanel.getByRole('button', { name: 'Salir sin guardar' }).click();
  await expect(page.locator('canvas.whiteboard-canvas')).toHaveCount(0);
  expect(saves).toHaveLength(1);
  expect(pageErrors).toEqual([]);
});
