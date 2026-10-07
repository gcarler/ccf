import { expect, test } from '@playwright/test';
import { installRuntimeGuards, waitForStableRoute } from '../helpers/runtimeGuards';

test('Mis tareas consume la colección paginada y renderiza sin mutaciones', async ({ page }) => {
  const runtime = installRuntimeGuards(page);
  const mutationRequests: string[] = [];
  const taskPageRequests: string[] = [];

  await page.setViewportSize({ width: 390, height: 844 });
  await page.route('**/api/**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (request.method() !== 'GET') {
      mutationRequests.push(`${request.method()} ${url.pathname}`);
      await route.fulfill({
        status: 405,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'E2E de solo lectura: mutación bloqueada' }),
      });
      return;
    }

    let body: unknown = [];
    if (url.pathname.endsWith('/v3/auth/me')) {
      body = {
        auth_user_id: 'projects-tasks-readonly-e2e',
        username: 'projects.tasks.e2e',
        email: 'projects.tasks.e2e@ccf.local',
        platform_role: 'GESTOR',
        is_verified: true,
        permissions: { 'projects:read': 'allow', 'projects:edit': 'allow' },
      };
    } else if (url.pathname === '/api/projects/tasks/page') {
      taskPageRequests.push(`${url.searchParams.get('offset')}:${url.searchParams.get('limit')}`);
      body = {
        items: [{
          id: '00000000-0000-4000-8000-000000000051',
          project_id: '00000000-0000-4000-8000-000000000052',
          project_title: 'Proyecto de lectura E2E',
          title: 'Tarea paginada visible E2E',
          status: 'in_progress',
          priority: 'medium',
          start_date: null,
          due_date: null,
        }],
        total: 1,
        skip: 0,
        limit: 100,
      };
    } else if (url.pathname.endsWith('/workspace/config')) {
      body = {};
    }

    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
  });

  await page.addInitScript(() => {
    sessionStorage.setItem('ccf_token', 'projects-tasks-readonly-e2e-token');
    sessionStorage.setItem('ccf_refresh_token', 'projects-tasks-readonly-e2e-refresh');
  });

  await waitForStableRoute(page, '/plataforma/projects/tasks?scope=mine&view=list');
  await expect(page.getByRole('heading', { name: 'Tarea paginada visible E2E' })).toBeVisible();

  const mobileView = page.getByRole('combobox', { name: 'Vista de tareas' });
  const mobileSearch = page.getByRole('searchbox', { name: 'Buscar tareas' });
  await mobileView.selectOption('table');
  await expect(page.getByRole('cell', { name: 'Tarea paginada visible E2E' })).toBeVisible();
  await mobileSearch.fill('paginada');
  await expect(page.getByRole('cell', { name: 'Tarea paginada visible E2E' })).toBeVisible();
  await mobileSearch.fill('no coincide');
  await expect(page.getByText('No hay tareas asignadas para este filtro.')).toBeVisible();
  await mobileSearch.fill('');
  await mobileView.selectOption('grid');
  await expect(page.getByRole('heading', { name: 'Tarea paginada visible E2E' })).toBeVisible();

  await page.setViewportSize({ width: 1280, height: 900 });
  const desktopSearch = page.getByRole('textbox', { name: 'Buscar en esta vista' });
  await expect(desktopSearch).toBeVisible();
  await desktopSearch.fill('no coincide');
  await expect(page.getByText('No hay tareas asignadas para este filtro.')).toBeVisible();
  await desktopSearch.fill('');
  await expect(page.getByRole('heading', { name: 'Tarea paginada visible E2E' })).toBeVisible();

  await page.setViewportSize({ width: 390, height: 844 });

  const widths = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    content: document.documentElement.scrollWidth,
  }));
  expect(widths.content, 'La vista de tareas no debe desbordarse en móvil').toBeLessThanOrEqual(widths.viewport + 1);
  expect(taskPageRequests).toEqual(['0:100']);
  expect(mutationRequests).toEqual([]);
  expect(runtime.assetErrors).toEqual([]);
  expect(runtime.apiErrors).toEqual([]);
  expect(runtime.pageErrors).toEqual([]);
  expect(runtime.consoleErrors).toEqual([]);
});
