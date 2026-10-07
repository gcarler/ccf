import { expect, test, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { waitForStableRoute } from '../helpers/runtimeGuards';

const projectId = '00000000-0000-4000-8000-000000000061';

const project = {
  id: projectId,
  title: 'Proyecto carga responsive',
  description: 'Fixture solo lectura para validar carga del equipo en móvil.',
  status: 'active',
  color: null,
  owner_id: null,
  progress_percent: 35,
  tasks: [],
  milestones: [],
  created_at: '2026-10-01T10:00:00Z',
  updated_at: '2026-10-01T10:00:00Z',
};

const workload = {
  project_id: projectId,
  total_members: 1,
  total_active_tasks: 1,
  total_completed_tasks: 0,
  total_overdue_tasks: 0,
  overloaded_members_count: 0,
  balanced_members_count: 1,
  available_members_count: 0,
  unassigned_tasks_count: 0,
  members: [
    {
      persona_id: '00000000-0000-4000-8000-000000000062',
      name: 'Ana Proyecto',
      total_tasks: 1,
      active_tasks: 1,
      completed_tasks: 0,
      overdue_tasks: 0,
      urgent_tasks: 0,
      high_tasks: 1,
      medium_tasks: 0,
      low_tasks: 0,
      capacity_status: 'balanced',
      workload_percent: 40,
      tasks: [
        {
          id: '00000000-0000-4000-8000-000000000063',
          title: 'Preparar materiales comunitarios',
          status: 'in_progress',
          priority: 'high',
          is_overdue: false,
        },
      ],
    },
  ],
};

const riskSummary = {
  project_id: projectId,
  total_risks: 0,
  active_risks: 0,
  mitigated_risks: 0,
  occurred_risks: 0,
  critical_count: 0,
  high_count: 0,
  medium_count: 0,
  low_count: 0,
  matrix_5x5: [],
  by_category: {},
};

const executiveReport = {
  project: {
    id: projectId,
    title: project.title,
    description: project.description,
    status: project.status,
    priority: 'medium',
    progress_percentage: 35,
    budget_allocated: 0,
    budget_spent: 0,
    owner_name: 'Sin responsable',
  },
  tasks_metrics: { total: 1, completed: 0, in_progress: 1, todo: 0, blocked: 0, completion_rate: 0 },
  financial_kpis: {
    project_id: projectId,
    budget_allocated: 0,
    budget_spent: 0,
    remaining_budget: 0,
    burn_rate_percent: 0,
    total_expenses_count: 0,
    by_category: {},
  },
  raid_kpis: { total_risks: 0, critical_count: 0, high_count: 0, medium_count: 0, low_count: 0, risks: [] },
  cpm_metrics: { project_id: projectId, total_duration_days: 0, critical_tasks_count: 0, critical_path_task_ids: [], tasks: [] },
  time_metrics: { total_hours: 0, billable_hours: 0, non_billable_hours: 0, total_logs: 0, by_task: [], by_member: [] },
  phases: [],
  generated_at: '2026-10-05T10:00:00Z',
  organization: 'CCF',
};

async function expectNoSeriousAccessibilityViolations(page: Page, selector: string) {
  const results = await new AxeBuilder({ page })
    .include(selector)
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze();
  const violations = results.violations.filter(
    (violation) => violation.impact === 'serious' || violation.impact === 'critical',
  );
  expect(violations.map((violation) => ({
    id: violation.id,
    impact: violation.impact,
    nodes: violation.nodes.map((node) => ({
      target: node.target,
      failureSummary: node.failureSummary,
    })),
  }))).toEqual([]);
}

test('ProjectWorkloadDrawer fits mobile viewport and remains accessible with real drawer chrome', async ({ page }) => {
  const mutationRequests: string[] = [];
  const pageErrors: string[] = [];
  const consoleErrors: string[] = [];
  const apiResponses: string[] = [];
  page.on('pageerror', (error) => pageErrors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });
  page.on('response', (response) => {
    if (response.url().includes('/api/')) {
      apiResponses.push(`${response.status()} ${new URL(response.url()).pathname}`);
    }
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.routeWebSocket('**/messaging/ws/**', (socket) => {
    socket.onMessage(() => undefined);
  });
  await page.route('**/api/**', async (route) => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname;
    if (request.method() !== 'GET') {
      mutationRequests.push(`${request.method()} ${pathname}`);
      await route.fulfill({ status: 405, body: 'Read-only workload test' });
      return;
    }

    let body: unknown = [];
    if (pathname.endsWith('/v3/auth/me')) {
      body = {
        auth_user_id: 'workload-responsive-e2e-user',
        username: 'workload.responsive.e2e',
        email: 'workload.responsive@ccf.local',
        platform_role: 'GESTOR',
        is_verified: true,
        permissions: { 'projects:read': 'allow', 'projects:edit': 'allow' },
      };
    } else if (pathname === `/api/projects/${projectId}`) {
      body = project;
    } else if (pathname === `/api/projects/${projectId}/workload`) {
      body = workload;
    } else if (pathname === `/api/projects/${projectId}/kpis`) {
      body = [];
    } else if (pathname === `/api/projects/${projectId}/budget-summary`) {
      body = {
        project_id: projectId,
        budget_allocated: 0,
        budget_spent: 0,
        remaining_budget: 0,
        burn_rate_percent: 0,
        total_expenses_count: 0,
        planned_amount: 0,
        committed_amount: 0,
        paid_amount: 0,
        by_category: {},
      };
    } else if (pathname === `/api/projects/${projectId}/risks-summary`) {
      body = riskSummary;
    } else if (pathname === `/api/projects/${projectId}/time-tracking-summary`) {
      body = {
        project_id: projectId,
        total_hours: 0,
        billable_hours: 0,
        non_billable_hours: 0,
        total_logs: 0,
        by_task: [],
        by_member: [],
      };
    } else if (pathname === `/api/projects/${projectId}/analytics`) {
      body = {
        project_id: projectId,
        total_tasks: 0,
        completed_tasks: 0,
        open_tasks: 0,
        overdue_tasks: 0,
        unassigned_tasks: 0,
        velocity: 0,
        velocity_unit: 'tareas/día',
        overdue_days: 0,
        risk_level: 'bajo',
        risk_reason: 'Sin bloqueos',
        health_score: 100,
        health_label: 'óptima',
      };
    } else if (pathname === `/api/projects/${projectId}/export/executive-data`) {
      body = executiveReport;
    } else if (pathname.endsWith('/workspace/config')) {
      body = {};
    }

    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
  });
  await page.addInitScript(() => {
    sessionStorage.setItem('ccf_token', 'workload-responsive-e2e-token');
    sessionStorage.setItem('ccf_refresh_token', 'workload-responsive-e2e-refresh');
  });

  await waitForStableRoute(page, `/plataforma/projects/${projectId}`);
  if (!(await page.getByRole('heading', { name: project.title }).isVisible().catch(() => false))) {
    throw new Error(`Project detail did not load. Alerts: ${JSON.stringify(await page.getByRole('alert').allInnerTexts())}; text: ${JSON.stringify((await page.locator('body').innerText()).slice(-500))}; API: ${apiResponses.join(', ')}; page errors: ${pageErrors.join(', ')}; console: ${consoleErrors.join(' | ')}`);
  }
  await expect(page.getByRole('heading', { name: project.title })).toBeVisible();
  await page.getByRole('button', { name: 'Abrir acciones del proyecto' }).click();
  await page.getByRole('dialog', { name: 'Acciones del proyecto' }).getByRole('button', { name: 'Carga' }).click();

  const drawerName = 'Capacidad de Equipo y Carga de Trabajo';
  const drawer = page.getByRole('dialog', { name: drawerName });
  const drawerSelector = `[role="dialog"][aria-label="${drawerName}"]`;
  await expect(drawer.getByText('Preparar materiales comunitarios')).toBeVisible();
  await expect(drawer.getByRole('progressbar', { name: 'Carga de Ana Proyecto' })).toHaveAttribute('aria-valuenow', '40');
  await expect(drawer).toHaveCSS('transform', 'none');

  const geometry = await drawer.evaluate((element) => {
    const rect = element.getBoundingClientRect();
    return {
      left: rect.left,
      right: rect.right,
      width: rect.width,
      clientWidth: element.clientWidth,
      scrollWidth: element.scrollWidth,
      viewportWidth: document.documentElement.clientWidth,
      documentWidth: document.documentElement.scrollWidth,
    };
  });
  expect(geometry.left).toBeGreaterThanOrEqual(0);
  expect(geometry.right).toBeLessThanOrEqual(geometry.viewportWidth + 1);
  expect(geometry.scrollWidth).toBeLessThanOrEqual(geometry.clientWidth + 1);
  expect(geometry.documentWidth).toBeLessThanOrEqual(geometry.viewportWidth + 1);
  await expectNoSeriousAccessibilityViolations(page, drawerSelector);

  await page.keyboard.press('Escape');
  await expect(drawer).toHaveCount(0);

  await page.getByRole('button', { name: 'Abrir acciones del proyecto' }).click();
  await page.getByRole('dialog', { name: 'Acciones del proyecto' }).getByRole('button', { name: 'Reportes' }).click();

  const reportName = 'Reportes y Exportación Ejecutiva';
  const reportDrawer = page.getByRole('dialog', { name: reportName });
  const reportSelector = `[role="dialog"][aria-label="${reportName}"]`;
  await expect(reportDrawer.getByText('Distribución de Horas y Esfuerzo')).toBeVisible();
  await expect(reportDrawer).toHaveCSS('transform', 'none');

  const reportGeometry = await reportDrawer.evaluate((element) => {
    const rect = element.getBoundingClientRect();
    return {
      left: rect.left,
      right: rect.right,
      scrollWidth: element.scrollWidth,
      clientWidth: element.clientWidth,
      viewportWidth: document.documentElement.clientWidth,
      documentWidth: document.documentElement.scrollWidth,
    };
  });
  expect(reportGeometry.left).toBeGreaterThanOrEqual(0);
  expect(reportGeometry.right).toBeLessThanOrEqual(reportGeometry.viewportWidth + 1);
  expect(reportGeometry.scrollWidth).toBeLessThanOrEqual(reportGeometry.clientWidth + 1);
  expect(reportGeometry.documentWidth).toBeLessThanOrEqual(reportGeometry.viewportWidth + 1);
  await expectNoSeriousAccessibilityViolations(page, reportSelector);

  await page.keyboard.press('Escape');
  await expect(reportDrawer).toHaveCount(0);
  expect(mutationRequests).toEqual([]);
  expect(pageErrors).toEqual([]);
});
