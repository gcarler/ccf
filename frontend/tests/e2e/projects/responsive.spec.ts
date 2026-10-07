import { expect, test, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

async function expectNoSeriousAccessibilityViolations(page: Page) {
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa'])
    .analyze();
  const blocking = results.violations.filter(
    (violation) => violation.impact === 'serious' || violation.impact === 'critical',
  );
  expect(blocking.map((violation) => ({
    id: violation.id,
    impact: violation.impact,
    nodes: violation.nodes.map((node) => node.target),
  }))).toEqual([]);
}

const demoProject = {
  id: 'project-responsive-e2e',
  title: 'Proyecto E2E Responsive',
  description: 'Proyecto de lectura para validar navegación responsive.',
  status: 'active',
  color: null,
  owner_id: null,
  progress_percent: 35,
  tasks: [],
  milestones: [],
  created_at: '2026-10-01T10:00:00Z',
  updated_at: '2026-10-01T10:00:00Z',
};

test('Projects muestra métricas solo en Resumen y conserva navegación responsive sin mutaciones', async ({ page }) => {
  const mutationRequests: string[] = [];
  const permissions: Record<string, 'allow' | 'deny'> = {
    'projects:read': 'allow',
    'projects:edit': 'allow',
    'projects:manage': 'allow',
    'academy:manage': 'allow',
  };
  await page.setViewportSize({ width: 390, height: 844 });
  await page.route('**/api/**', async (route) => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname;
    if (request.method() !== 'GET') {
      mutationRequests.push(`${request.method()} ${pathname}`);
      await route.fulfill({
        status: 405,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'E2E de solo lectura' }),
      });
      return;
    }

    let body: unknown = [];
    if (pathname.endsWith('/v3/auth/me')) {
      body = {
        auth_user_id: 'e2e-projects-user',
        username: 'projects.e2e',
        email: 'projects.e2e@ccf.local',
        platform_role: 'GESTOR',
        is_verified: true,
        permissions,
      };
    } else if (pathname.endsWith('/dashboard/projects')) {
      body = {
        cards: [{ title: 'Proyectos activos', value: '1', trend: null, tone: 'primary' }],
        workload_distribution: [],
        delayed_tasks_count: 0,
      };
    } else if (pathname.endsWith('/projects/summary-page')) {
      const search = new URL(request.url()).searchParams.get('search')?.trim().toLowerCase();
      const items = search && !demoProject.title.toLowerCase().includes(search) ? [] : [demoProject];
      body = { items, total: items.length, skip: 0, limit: 50 };
    } else if (pathname === '/api/wiki/pages/wiki_projects_portfolio') {
      body = { title: 'Wiki Proyectos', content: '' };
    } else if (pathname.endsWith('/workspace/config')) {
      body = {};
    }

    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
  });
  await page.addInitScript(() => {
    sessionStorage.setItem('ccf_token', 'projects-responsive-e2e-token');
    sessionStorage.setItem('ccf_refresh_token', 'projects-responsive-e2e-refresh');
  });

  await page.goto('/plataforma/projects', { waitUntil: 'domcontentloaded' });
  await expect(page.getByTestId('projects-overview')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Abrir proyecto Proyecto E2E Responsive' })).toBeVisible();
  await expectNoSeriousAccessibilityViolations(page);
  const deleteAction = page.getByRole('button', { name: 'Eliminar proyecto' });
  await expect(deleteAction).toBeVisible();
  await expect(page.locator('[data-workspace-toolbar]')).toHaveCount(1);

  // A system configuration grant must not substitute for the backend's
  // academy:manage requirement on DELETE /projects/{project_id}.
  delete permissions['academy:manage'];
  permissions['system:config'] = 'allow';
  await page.reload({ waitUntil: 'domcontentloaded' });
  await expect(page.getByRole('link', { name: 'Abrir proyecto Proyecto E2E Responsive' })).toBeVisible();
  await expect(deleteAction).toHaveCount(0);

  await page.getByRole('combobox', { name: 'Vista de proyectos' }).selectOption('calendar');
  await expect(page.getByTestId('projects-overview')).toHaveCount(0);
  await expect(page.getByText('Calendario de proyectos')).toBeVisible();
  await expect(page.locator('[data-workspace-toolbar]')).toHaveCount(1);
  await expectNoSeriousAccessibilityViolations(page);

  await page.getByRole('combobox', { name: 'Vista de proyectos' }).selectOption('list');
  const listView = page.locator('#projects-dashboard');
  await expect(listView.getByRole('button', { name: 'Abrir proyecto Proyecto E2E Responsive' })).toBeVisible();
  await expect(page.getByTestId('projects-overview')).toHaveCount(0);
  await expect(page.locator('[data-workspace-toolbar]')).toHaveCount(1);
  await expectNoSeriousAccessibilityViolations(page);
  const widths = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    content: document.documentElement.scrollWidth,
  }));
  expect(widths.content, 'Projects must not create horizontal page overflow at 390px').toBeLessThanOrEqual(widths.viewport + 1);
  await page.getByRole('searchbox', { name: 'Buscar proyectos' }).fill('sin coincidencias');
  await expect(page.getByText('Ningún proyecto coincide con tu búsqueda.')).toBeVisible();

  await page.getByRole('searchbox', { name: 'Buscar proyectos' }).fill('');
  await page.getByRole('combobox', { name: 'Vista de proyectos' }).selectOption('gantt');
  await expect(page.getByRole('button', { name: 'Día' })).toBeVisible();
  await expect(page.getByTestId('projects-overview')).toHaveCount(0);
  await expect(page.locator('[data-workspace-toolbar]')).toHaveCount(1);
  await expectNoSeriousAccessibilityViolations(page);

  await page.getByRole('combobox', { name: 'Vista de proyectos' }).selectOption('wiki');
  await expect(page.getByRole('heading', { name: 'Wiki Proyectos', level: 2 })).toBeVisible();
  await expect(page.getByTestId('projects-overview')).toHaveCount(0);
  await expect(page.locator('[data-workspace-toolbar]')).toHaveCount(1);
  await expectNoSeriousAccessibilityViolations(page);

  await page.getByRole('combobox', { name: 'Vista de proyectos' }).selectOption('dashboard');
  await expect(page.getByTestId('projects-overview')).toBeVisible();
  await expect(page.locator('[data-workspace-toolbar]')).toHaveCount(1);
  expect(mutationRequests).toEqual([]);
});
