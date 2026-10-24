import { expect, test } from '@playwright/test';
import { waitForStableRoute } from '../helpers/runtimeGuards';

test.setTimeout(180000);

const id = '00000000-0000-4000-8000-000000000061';

test('project tools share one resizable drawer and retain width across tools and mobile', async ({
  page,
}) => {
  page.setDefaultTimeout(15000);
  const pageErrors: string[] = [];
  const projectMutations: string[] = [];
  page.on('pageerror', error => pageErrors.push(error.message));
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.routeWebSocket('**/messaging/ws/**', socket =>
    socket.onMessage(() => undefined)
  );
  await page.route('**/api/**', async route => {
    const path = new URL(route.request().url()).pathname;
    if (
      path.startsWith('/api/projects') &&
      route.request().method() !== 'GET'
    ) {
      projectMutations.push(path);
      await route.fulfill({ status: 405, body: 'Read-only UI test' });
      return;
    }
    let body: unknown = [];
    if (path.endsWith('/v3/auth/me'))
      body = {
        auth_user_id: id,
        username: 'panel.review',
        email: 'panel@ccf.local',
        platform_role: 'GESTOR',
        is_verified: true,
        permissions: { 'projects:read': 'allow', 'projects:edit': 'allow' },
      };
    else if (path === `/api/projects/${id}`)
      body = {
        id,
        title: 'Proyecto revisión de paneles',
        status: 'active',
        tasks: [],
        milestones: [],
        progress_percent: 0,
        created_at: '2026-10-01T10:00:00Z',
        updated_at: '2026-10-01T10:00:00Z',
      };
    else if (path.endsWith('/wbs-tree'))
      body = {
        project_id: id,
        project_title: 'Proyecto revisión de paneles',
        total_nodes: 1,
        max_depth: 0,
        root: {
          id,
          title: 'Proyecto revisión de paneles',
          type: 'project',
          wbs_code: '0',
          level: 0,
          status: 'active',
          progress_pct: 0,
          estimated_hours: 0,
          actual_hours: 0,
          budget_allocated: 0,
          cost: 0,
          is_leaf: true,
          children: [],
        },
      };
    else if (path.endsWith('/analytics'))
      body = {
        risk_level: 'bajo',
        risk_reason: 'Sin bloqueos',
        health_label: 'óptima',
        health_score: 100,
        total_tasks: 0,
        completed_tasks: 0,
        open_tasks: 0,
        overdue_tasks: 0,
      };
    else if (path.endsWith('/evm/curve-s'))
      body = {
        project_id: id,
        summary: {
          project_id: id,
          calculated_at: '2026-10-22T00:00:00Z',
          bac: 100000,
          ac: 45000,
          ev: 50000,
          pv: 48000,
          progress_percentage: 50,
          financial_percentage: 45,
          cpi: 1.11,
          spi: 1.04,
          cv: 5000,
          sv: 2000,
          cr: 1.15,
          eac: 90090,
          vac: 9910,
          health_status: 'OPTIMO',
          health_color: 'success',
          recommendations: [],
        },
        points: [],
      };
    else if (path.endsWith('/workspace/config')) body = {};
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(body),
    });
  });
  await page.addInitScript(() => {
    sessionStorage.setItem('ccf_token', 'panel-review-token');
    sessionStorage.setItem('ccf_refresh_token', 'panel-review-refresh');
  });
  await waitForStableRoute(page, `/plataforma/projects/${id}?view=list`);
  const context = page.getByRole('complementary', {
    name: 'Contexto del proyecto',
  });
  await expect(context).toBeVisible({ timeout: 30000 });
  const contextHandle = context.getByRole('separator');
  await contextHandle.focus();
  await page.keyboard.press('ArrowLeft');
  await expect(contextHandle).toHaveAttribute('aria-valuenow', '404');
  await context.getByRole('tab', { name: 'Herramientas' }).click();
  await expect(
    context.getByRole('button', { name: 'Componentes EDT', exact: true })
  ).toBeVisible();
  await context
    .getByRole('button', { name: 'EDT / WBS y Diccionario', exact: true })
    .click();
  const hub = page.getByRole('dialog', {
    name: 'Centro de gestión del proyecto',
  });
  await expect(hub).toBeVisible();
  await expect(hub).toHaveCSS('transform', 'none');
  await expect(page.getByRole('dialog')).toHaveCount(1);
  await expect(hub.getByTestId('project-wbs-drawer')).toBeVisible();
  await expect(hub.getByRole('separator')).toHaveAttribute(
    'aria-valuenow',
    '960'
  );
  await hub.getByRole('separator').focus();
  await page.keyboard.press('ArrowRight');
  await expect(hub).toHaveCSS('width', '936px');
  const handleBox = await hub.getByRole('separator').boundingBox();
  if (!handleBox) throw new Error('Resize handle is missing');
  await page.mouse.move(handleBox.x + 4, handleBox.y + 100);
  await page.mouse.down();
  await page.mouse.move(handleBox.x - 96, handleBox.y + 100, { steps: 6 });
  await page.mouse.up();
  await expect(hub).toHaveCSS('width', '1036px');
  await hub
    .getByRole('button', { name: 'Pantalla completa', exact: true })
    .click();
  await hub
    .getByRole('button', { name: 'Salir de pantalla completa', exact: true })
    .click();
  await expect(hub).toHaveCSS('width', '1036px');
  await hub
    .getByRole('combobox', { name: 'Abrir herramienta' })
    .selectOption('components');
  await expect(page.getByRole('dialog')).toHaveCount(1);
  await expect(hub).toHaveCSS('width', '1036px');
  await hub.getByRole('tab', { name: /EDT \/ WBS y Diccionario/ }).click();
  await expect(hub.getByTestId('project-wbs-drawer')).toBeVisible();
  await expect(
    hub.getByRole('tab', { name: /EDT \/ WBS y Diccionario/ })
  ).toHaveAttribute('aria-selected', 'true');
  for (const [key, heading] of [
    ['kpis', 'Metas Operativas & 6 Familias Pro'],
    ['indicators', 'Indicadores y Resultados'],
    ['evm', 'Curva S de Desempeño Acumulado'],
  ]) {
    await hub
      .getByRole('combobox', { name: 'Abrir herramienta' })
      .selectOption(key);
    await expect(
      hub.getByRole('heading', { name: heading, exact: true })
    ).toBeVisible();
    await expect(page.getByRole('dialog')).toHaveCount(1);
    await hub.getByRole('separator').focus();
    await page.keyboard.press('ArrowRight');
    await expect(hub).toHaveCSS('width', '1012px');
    await page.keyboard.press('ArrowLeft');
    await expect(hub).toHaveCSS('width', '1036px');
  }
  await hub.getByRole('tab', { name: /EDT \/ WBS y Diccionario/ }).click();
  await expect(hub.getByRole('tab', { name: /EDT \/ WBS y Diccionario/ })).toHaveAttribute('aria-selected', 'true');
  await page.screenshot({ path: '/tmp/ccf-project-tools-desktop.png' });
  await hub.getByRole('button', { name: 'Cerrar panel', exact: true }).click();
  await context
    .getByRole('button', { name: 'EDT / WBS y Diccionario', exact: true })
    .click();
  await expect(hub).toHaveCSS('width', '1036px');
  await page.reload();
  await context.getByRole('tab', { name: 'Herramientas' }).click();
  await context
    .getByRole('button', { name: 'EDT / WBS y Diccionario', exact: true })
    .click();
  await expect(hub).toHaveCSS('width', '1036px');
  await hub.getByRole('separator').focus();
  await page.keyboard.press('Home');
  await expect(hub).toHaveCSS('width', '300px');
  expect(await hub.getByRole('region', { name: 'Validación de la Regla del 100%' }).evaluate(el => el.scrollWidth <= el.clientWidth + 1)).toBe(true);
  await expect(hub).toHaveCSS('transform', 'none');
  await page.screenshot({ path: '/tmp/ccf-project-tools-narrow.png' });
  await hub.getByRole('separator').dblclick();
  await expect(hub).toHaveCSS('width', '960px');
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(hub).toHaveCSS('width', '390px');
  await expect(hub.getByRole('separator')).toHaveCount(0);
  expect(await hub.evaluate(el => el.scrollWidth <= el.clientWidth + 1)).toBe(
    true
  );
  await page.screenshot({ path: '/tmp/ccf-project-tools-mobile.png' });
  expect(
    await hub.evaluate(el => el.contains(document.elementFromPoint(5, 200)))
  ).toBe(true);
  expect(projectMutations).toEqual([]);
  expect(pageErrors).toEqual([]);
});
