import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { installRuntimeGuards, waitForStableRoute } from '../helpers/runtimeGuards';

const projectId = '00000000-0000-4000-8000-000000000041';
const predecessorId = '00000000-0000-4000-8000-000000000042';
const successorId = '00000000-0000-4000-8000-000000000043';

const project = {
  id: projectId,
  title: 'Proyecto Gantt de solo lectura',
  description: 'Fixture de navegador sin acceso a base de datos.',
  status: 'active',
  color: null,
  owner_id: null,
  progress_percent: 25,
  milestones: [],
  created_at: '2026-10-01T10:00:00Z',
  updated_at: '2026-10-02T10:00:00Z',
};

const tasks = [
  {
    id: predecessorId,
    project_id: projectId,
    title: 'Tarea predecesora E2E',
    status: 'in_progress',
    priority: 'medium',
    start_date: '2026-10-01T10:00:00Z',
    due_date: '2026-10-03T10:00:00Z',
    order_index: 0,
  },
  {
    id: successorId,
    project_id: projectId,
    title: 'Tarea sucesora E2E',
    status: 'todo',
    priority: 'high',
    start_date: '2026-10-04T10:00:00Z',
    due_date: '2026-10-06T10:00:00Z',
    order_index: 1,
  },
];

async function expectNoSeriousAccessibilityViolations(
  page: import('@playwright/test').Page,
  scope?: string,
) {
  if (scope) await expect(page.locator(scope)).toHaveCSS('opacity', '1');
  const builder = new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']);
  if (scope) builder.include(scope);
  const results = await builder
    .analyze();
  expect(results.violations.map((violation) => ({
    id: violation.id,
    impact: violation.impact,
    nodes: violation.nodes.map((node) => ({ target: node.target, failureSummary: node.failureSummary })),
  }))).toEqual([]);
}

test('Projects Gantt valida dependencias y estados con API mockeada sin mutaciones', async ({ page }) => {
  const runtime = installRuntimeGuards(page);
  const mutationRequests: string[] = [];
  const relevantReads = new Set<string>();

  await page.setViewportSize({ width: 390, height: 844 });
  await page.routeWebSocket('**/messaging/ws/**', (socket) => {
    socket.onMessage(() => undefined);
  });

  await page.route('**/api/**', async (route) => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname;
    if (request.method() !== 'GET') {
      mutationRequests.push(`${request.method()} ${pathname}`);
      await route.fulfill({
        status: 405,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'E2E de solo lectura: mutación bloqueada' }),
      });
      return;
    }

    let body: unknown = [];
    if (pathname.endsWith('/v3/auth/me')) {
      body = {
        auth_user_id: 'projects-gantt-readonly-e2e',
        username: 'projects.gantt.e2e',
        email: 'projects.gantt.e2e@ccf.local',
        platform_role: 'GESTOR',
        is_verified: true,
        permissions: { 'projects:read': 'allow', 'projects:edit': 'allow' },
      };
    } else if (pathname === `/api/projects/${projectId}`) {
      relevantReads.add('project');
      body = project;
    } else if (pathname === `/api/projects/${projectId}/tasks`) {
      relevantReads.add('tasks');
      body = tasks;
    } else if (pathname === '/api/projects/activities') {
      relevantReads.add('activities');
      body = [];
    } else if (pathname === `/api/projects/${projectId}/phases`) {
      relevantReads.add('phases');
      body = [{ slug: 'in_progress', name: 'En curso', color: null, order_index: 0 }];
    } else if (pathname === `/api/projects/${projectId}/dependencies`) {
      relevantReads.add('dependencies');
      body = [];
    } else if (pathname === `/api/projects/${projectId}/critical-path`) {
      relevantReads.add('critical-path');
      body = {
        project_id: projectId,
        total_duration_days: 5,
        critical_tasks_count: 1,
        critical_path_task_ids: [predecessorId],
        tasks: [],
        has_cycles: false,
      };
    } else if (pathname === `/api/projects/${projectId}/baseline`) {
      relevantReads.add('baseline');
      body = null;
    } else if (pathname === `/api/projects/${projectId}/baselines`) {
      relevantReads.add('baselines');
      body = [];
    }

    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
  });

  await page.addInitScript(() => {
    sessionStorage.setItem('ccf_token', 'projects-gantt-readonly-e2e-token');
    sessionStorage.setItem('ccf_refresh_token', 'projects-gantt-readonly-e2e-refresh');
  });

  const detailPath = `/plataforma/projects/${projectId}?view=gantt`;
  await waitForStableRoute(page, detailPath);
  await expect(page.getByRole('heading', { name: 'Gantt PRO & Cronograma' })).toBeVisible();
  await expect(page.locator('[data-workspace-toolbar]')).toHaveCount(1);
  await expect(page.getByTestId('projects-overview')).toHaveCount(0);
  await expect(page.getByText('Tarea predecesora E2E').first()).toBeVisible();
  await expect(page.getByText('Tarea sucesora E2E').first()).toBeVisible();
  await expectNoSeriousAccessibilityViolations(page);
  const createTaskAction = page.getByRole('button', { name: /Nueva tarea/i });
  const openActions = page.getByRole('button', { name: 'Abrir acciones del proyecto' });
  await expect(createTaskAction).toBeVisible();
  await expect(openActions).toBeVisible();
  for (const control of [createTaskAction, openActions]) {
    const bounds = await control.boundingBox();
    expect(bounds, 'Las acciones primarias deben tener geometría visible en móvil').not.toBeNull();
    expect(bounds!.x).toBeGreaterThanOrEqual(0);
    expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(391);
  }
  await openActions.click();
  const actionsDrawer = page.getByRole('dialog', { name: 'Acciones del proyecto' });
  await expect(actionsDrawer).toBeVisible();
  await expectNoSeriousAccessibilityViolations(page, '[role="dialog"][aria-label="Acciones del proyecto"]');
  for (const actionName of ['Pizarra', 'Fases', 'Presupuesto', 'Riesgos', 'Automatizaciones', 'MGA / CREMA', 'Editar proyecto']) {
    await expect(actionsDrawer.getByRole('button', { name: actionName })).toBeVisible();
  }
  const closeActions = actionsDrawer.getByRole('button', { name: 'Cerrar panel' });
  await expect(closeActions).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(actionsDrawer).toHaveCount(0);
  await expect(openActions).toBeFocused();

  const mobileWidths = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    content: document.documentElement.scrollWidth,
  }));
  expect(mobileWidths.content, 'El detalle Gantt no debe desbordarse en móvil').toBeLessThanOrEqual(mobileWidths.viewport + 1);
  for (const name of ['Alternar ruta crítica', 'Alternar línea base', 'Fijar Base', 'Conectar dependencia']) {
    const control = page.getByRole('button', { name });
    await expect(control).toBeVisible();
    const bounds = await control.boundingBox();
    expect(bounds, `${name} debe tener geometría visible en móvil`).not.toBeNull();
    expect(bounds!.x, `${name} no debe quedar recortado por la izquierda`).toBeGreaterThanOrEqual(0);
    expect(bounds!.x + bounds!.width, `${name} no debe quedar recortado por la derecha`).toBeLessThanOrEqual(mobileWidths.viewport + 1);
  }

  const taskRow = page.getByRole('button', {
    name: 'Abrir detalle de tarea Tarea predecesora E2E desde la lista del Gantt',
  });
  await taskRow.focus();
  await page.keyboard.press('Enter');
  const taskDetail = page.getByRole('complementary', { name: 'Detalle de tarea' });
  await expect(taskDetail).toBeVisible();
  await expect(taskDetail.getByRole('button', { name: 'Cerrar detalle de tarea' })).toBeVisible();
  await expectNoSeriousAccessibilityViolations(page, '[aria-label="Detalle de tarea"]');
  const taskDetailBounds = await taskDetail.boundingBox();
  expect(taskDetailBounds, 'El detalle de tarea debe permanecer visible en móvil').not.toBeNull();
  expect(taskDetailBounds!.x).toBeGreaterThanOrEqual(0);
  expect(taskDetailBounds!.x + taskDetailBounds!.width).toBeLessThanOrEqual(mobileWidths.viewport + 1);
  await page.keyboard.press('Escape');
  await expect(taskDetail).toHaveCount(0);
  await expect(taskRow).toBeFocused();

  await page.getByRole('button', { name: 'Conectar dependencia' }).click();
  const dependencyDrawer = page.getByRole('dialog', { name: 'Vincular dependencia entre tareas' });
  await expect(dependencyDrawer).toBeVisible();
  await expectNoSeriousAccessibilityViolations(page, '[role="dialog"][aria-label="Vincular dependencia entre tareas"]');
  const dependencyType = dependencyDrawer.getByLabel('Tipo de Enlace');
  await dependencyDrawer.getByLabel(/Tarea Predecesora/).selectOption(predecessorId);
  await dependencyDrawer.getByLabel(/Tarea Sucesora/).selectOption(successorId);

  const descriptions: Record<string, string> = {
    FS: 'La tarea sucesora puede iniciar cuando finalice la predecesora.',
    SS: 'La tarea sucesora puede iniciar cuando comience la predecesora.',
    FF: 'La tarea sucesora puede finalizar cuando finalice la predecesora.',
    SF: 'La tarea sucesora puede finalizar cuando comience la predecesora.',
  };
  for (const [type, description] of Object.entries(descriptions)) {
    await dependencyType.selectOption(type);
    await expect(dependencyDrawer.getByText(description)).toBeVisible();
  }
  await dependencyDrawer.getByRole('button', { name: 'Cancelar' }).click();
  await expect(dependencyDrawer).toHaveCount(0);

  await page.getByRole('button', { name: 'Alternar ruta crítica' }).click();
  await expect(page.getByRole('button', { name: 'Alternar ruta crítica' })).toContainText('Ruta Crítica (1)');

  await page.getByRole('button', { name: 'Alternar línea base' }).click();
  await expect(page.getByText('No hay una línea base registrada.')).toBeVisible();

  await page.getByRole('button', { name: 'Fijar Base' }).click();
  const baselineDrawer = page.getByRole('dialog', { name: 'Línea Base y Control de Varianza (Gantt)' });
  await expect(baselineDrawer).toBeVisible();
  await expect(baselineDrawer.getByText('Sin Línea Base Registrada')).toBeVisible();
  await expectNoSeriousAccessibilityViolations(
    page,
    '[role="dialog"][aria-label="Línea Base y Control de Varianza (Gantt)"]',
  );
  const baselineDrawerBounds = await baselineDrawer.boundingBox();
  expect(baselineDrawerBounds, 'El panel de línea base debe permanecer visible en móvil').not.toBeNull();
  expect(baselineDrawerBounds!.x).toBeGreaterThanOrEqual(0);
  expect(baselineDrawerBounds!.x + baselineDrawerBounds!.width).toBeLessThanOrEqual(mobileWidths.viewport + 1);
  await baselineDrawer.getByRole('button', { name: 'Congelar Nueva Línea Base' }).click();
  await expect(baselineDrawer.getByLabel('Nombre de la Línea Base')).toBeVisible();
  await expect(baselineDrawer.getByLabel('Descripción / Motivo del Congelamiento (Opcional)')).toBeVisible();
  await expectNoSeriousAccessibilityViolations(
    page,
    '[role="dialog"][aria-label="Línea Base y Control de Varianza (Gantt)"]',
  );
  await page.keyboard.press('Escape');
  await expect(baselineDrawer).toHaveCount(0);

  expect([...relevantReads].sort()).toEqual([
    'activities', 'baseline', 'baselines', 'critical-path', 'dependencies', 'phases', 'project', 'tasks',
  ]);
  expect(mutationRequests).toEqual([]);
  expect(runtime.assetErrors).toEqual([]);
  expect(runtime.apiErrors).toEqual([]);
  expect(runtime.pageErrors).toEqual([]);
  expect(runtime.consoleErrors).toEqual([]);
});
