import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { waitForStableRoute } from '../helpers/runtimeGuards';

const projectId = '00000000-0000-4000-8000-000000000051';
const personaId = '00000000-0000-4000-8000-000000000052';

const project = {
  id: projectId,
  title: 'Proyecto RAID de navegador',
  description: 'Fixture de lectura/escritura simulada sin base de datos.',
  status: 'active',
  color: null,
  owner_id: null,
  progress_percent: 0,
  tasks: [],
  milestones: [],
  created_at: '2026-10-01T10:00:00Z',
  updated_at: '2026-10-01T10:00:00Z',
};

const summary = {
  project_id: projectId,
  total_risks: 1,
  active_risks: 1,
  mitigated_risks: 0,
  occurred_risks: 0,
  critical_count: 0,
  high_count: 0,
  medium_count: 1,
  low_count: 0,
  matrix_5x5: [],
  by_category: {},
};

async function expectNoAxeViolations(page: import('@playwright/test').Page, scope: string) {
  await expect(page.locator(scope)).toHaveCSS('opacity', '1');
  const results = await new AxeBuilder({ page })
    .include(scope)
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze();
  expect(results.violations.map((violation) => ({
    id: violation.id,
    impact: violation.impact,
    nodes: violation.nodes.map((node) => ({ target: node.target, failureSummary: node.failureSummary })),
  }))).toEqual([]);
}

test('RAID recovery and owner assignment stay inside mocked APIs', async ({ page }) => {
  const pageErrors: string[] = [];
  const mutationRequests: string[] = [];
  let riskReadAttempts = 0;
  let createdRisk: Record<string, unknown> | null = null;
  page.on('pageerror', (error) => pageErrors.push(error.message));

  await page.routeWebSocket('**/messaging/ws/**', (socket) => {
    socket.onMessage(() => undefined);
  });

  await page.route('**/api/**', async (route) => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname;
    if (request.method() !== 'GET') {
      mutationRequests.push(`${request.method()} ${pathname}`);
      if (request.method() === 'POST' && pathname === `/api/projects/${projectId}/risks`) {
        createdRisk = request.postDataJSON() as Record<string, unknown>;
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'risk-e2e-1',
            project_id: projectId,
            title: createdRisk.title,
            category: createdRisk.category,
            probability: createdRisk.probability,
            impact: createdRisk.impact,
            severity_score: Number(createdRisk.probability) * Number(createdRisk.impact),
            severity_level: 'medium',
            owner_id: createdRisk.owner_id,
            owner_name: 'Ana Proyecto',
            status: createdRisk.status,
            created_at: '2026-10-04T10:00:00Z',
          }),
        });
        return;
      }
      await route.fulfill({ status: 405, body: 'Unexpected mutation blocked by E2E' });
      return;
    }

    let body: unknown = [];
    if (pathname.endsWith('/v3/auth/me')) {
      body = {
        auth_user_id: 'projects-risk-matrix-e2e',
        username: 'projects.risk.e2e',
        email: 'projects.risk.e2e@ccf.local',
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
    } else if (pathname === `/api/projects/${projectId}/kpis`) {
      body = [];
    } else if (pathname === `/api/projects/${projectId}/budget-summary`) {
      body = { ...project, budget_allocated: 0, budget_spent: 0, remaining_budget: 0, burn_rate_percent: 0, by_category: {} };
    } else if (pathname === `/api/projects/${projectId}/risks-summary`) {
      body = summary;
    } else if (pathname === `/api/projects/${projectId}/workload`) {
      body = {
        project_id: projectId,
        total_members: 0,
        total_active_tasks: 0,
        total_completed_tasks: 0,
        total_overdue_tasks: 0,
        overloaded_members_count: 0,
        balanced_members_count: 0,
        available_members_count: 0,
        unassigned_tasks_count: 0,
        members: [],
      };
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
    } else if (pathname.startsWith('/api/crm/personas')) {
      body = [{ id: personaId, first_name: 'Ana', last_name: 'Proyecto' }];
    } else if (pathname === `/api/projects/${projectId}/risks`) {
      riskReadAttempts += 1;
      if (riskReadAttempts === 1) {
        await route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: 'E2E temporal failure' }) });
        return;
      }
      body = createdRisk
        ? [{
            id: 'risk-e2e-1',
            project_id: projectId,
            title: createdRisk.title,
            category: createdRisk.category,
            probability: createdRisk.probability,
            impact: createdRisk.impact,
            severity_score: Number(createdRisk.probability) * Number(createdRisk.impact),
            severity_level: 'medium',
            owner_id: createdRisk.owner_id,
            owner_name: 'Ana Proyecto',
            status: createdRisk.status,
            created_at: '2026-10-04T10:00:00Z',
          }]
        : [];
    }

    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
  });

  await page.addInitScript(() => {
    sessionStorage.setItem('ccf_token', 'projects-risk-matrix-e2e-token');
    sessionStorage.setItem('ccf_refresh_token', 'projects-risk-matrix-e2e-refresh');
  });

  await waitForStableRoute(page, `/plataforma/projects/${projectId}`);
  await page.getByRole('button', { name: 'Gestionar Riesgos (RAID)' }).click();
  const drawer = page.getByRole('dialog', { name: 'Matriz RAID de Riesgos y Supuestos' });
  await expect(drawer.getByRole('alert')).toContainText('No se pudo cargar la matriz de riesgos.');
  const drawerSelector = '[role="dialog"][aria-label="Matriz RAID de Riesgos y Supuestos"]';
  await expectNoAxeViolations(page, drawerSelector);
  await expect(drawer.getByText('No hay riesgos registrados con estos filtros')).toHaveCount(0);

  await drawer.getByRole('button', { name: 'Reintentar carga' }).click();
  await expect(drawer.getByText('No hay riesgos registrados con estos filtros')).toBeVisible();
  await expectNoAxeViolations(page, drawerSelector);
  await drawer.getByRole('button', { name: 'Registrar Riesgo' }).click();
  await drawer.getByPlaceholder(/ej\. Fallo en el servidor/).fill('Interrupción de servicio');
  await expectNoAxeViolations(page, drawerSelector);
  await drawer.getByRole('group', { name: 'Responsable del riesgo' }).getByRole('button').click();
  await drawer.getByRole('option', { name: 'Ana Proyecto' }).click();
  await expectNoAxeViolations(page, drawerSelector);
  await drawer.getByRole('button', { name: 'Guardar Riesgo' }).click();

  await expect(page.getByRole('status').filter({ hasText: 'Riesgo registrado en la matriz RAID' })).toBeVisible();
  await expect(drawer.getByText('Interrupción de servicio')).toBeVisible();
  await expectNoAxeViolations(page, drawerSelector);
  expect(createdRisk).toMatchObject({ title: 'Interrupción de servicio', owner_id: personaId });
  expect(mutationRequests).toEqual([`POST /api/projects/${projectId}/risks`]);
  expect(pageErrors).toEqual([]);
});
