import { expect, test, type Page } from '@playwright/test';
import { installMockPlatformSession } from '../helpers/mockPlatformSession';

const STAGES = [
  {
    id: 'stage-new',
    value: 'new',
    label: 'NUEVO',
    color: 'bg-[hsl(var(--primary))]',
    dot: 'bg-[hsl(var(--primary))]',
    text: 'text-[hsl(var(--primary))]',
    bg: 'bg-blue-50',
    border: 'border-blue-200',
  },
  {
    id: 'stage-call',
    value: 'call',
    label: 'POR LLAMAR',
    color: 'bg-amber-500',
    dot: 'bg-amber-500',
    text: 'text-amber-600',
    bg: 'bg-amber-50',
    border: 'border-amber-200',
  },
  {
    id: 'stage-consolidated',
    value: 'consolidated',
    label: 'CONSOLIDADO',
    color: 'bg-emerald-500',
    dot: 'bg-emerald-500',
    text: 'text-emerald-600',
    bg: 'bg-emerald-50',
    border: 'border-emerald-200',
  },
];

const CASES = [
  {
    id: 'lead-1',
    nombre_completo: 'Abigail Monsalve',
    telefono: '+57 300 123 4567',
    phone: '+57 300 123 4567',
    source: 'Visitante',
    stage: 'new',
    sort_order: 0,
    created_at: '2026-07-15T10:00:00Z',
  },
  {
    id: 'lead-2',
    nombre_completo: 'Carlos Rueda',
    telefono: '+57 300 987 6543',
    phone: '+57 300 987 6543',
    source: 'Referido',
    stage: 'call',
    sort_order: 0,
    created_at: '2026-07-16T12:00:00Z',
  },
];

async function installPipelineMocks(page: Page) {
  let createPayload: Record<string, unknown> | null = null;
  let reorderPayload: unknown = null;

  await installMockPlatformSession(page, {
    permissions: {
      'crm:read': 'allow',
      'crm:edit': 'allow',
      'crm:manage': 'allow',
    },
  });

  await page.addInitScript(() => {
    localStorage.setItem('crm_pipeline_view', 'table');
  });

  await page.route('**/api/crm/casos', async (route) => {
    if (route.request().method() === 'POST') {
      createPayload = route.request().postDataJSON() as Record<string, unknown>;
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'lead-new',
          ...createPayload,
        }),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(CASES),
    });
  });

  await page.route('**/api/crm/casos/lead-1/audit', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 'audit-1',
          action: 'update_pipeline_lead',
          created_at: '2026-07-16T14:00:00Z',
          metadata: { stage: 'new' },
        },
      ]),
    });
  });

  await page.route('**/api/crm/pipeline/kanban/stages', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(STAGES),
    });
  });

  await page.route('**/api/crm/pipeline/casos/reorder', async (route) => {
    reorderPayload = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'success' }),
    });
  });

  return {
    getCreatePayload: () => createPayload,
    getReorderPayload: () => reorderPayload,
  };
}

test.describe('CRM pipeline deep smoke', () => {
  test('creates a new prospect with the current pipeline contract', async ({ page }) => {
    const pipeline = await installPipelineMocks(page);

    await page.goto('/plataforma/crm/pipeline', { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    await expect(page.locator('body')).toContainText(/Pipeline de Consolidación/i);
    await expect(page.locator('body')).toContainText(/Abigail Monsalve/i);

    await page.getByRole('button', { name: /Nuevo Lead/i }).click();
    await page.getByPlaceholder('Juan').fill('Lucía');
    await page.getByPlaceholder('Pérez').fill('Herrera');
    await page.getByPlaceholder('+57 300 000 0000').fill('+57 301 000 0000');
    await page.getByRole('button', { name: /Registrar Prospecto/i }).click();

    await expect.poll(() => pipeline.getCreatePayload()).not.toBeNull();
    await expect
      .poll(() => (pipeline.getCreatePayload() as Record<string, unknown> | null)?.first_name)
      .toBe('Lucía');
  });

  test('opens a lead and updates its stage through the canonical reorder endpoint', async ({ page }) => {
    const pipeline = await installPipelineMocks(page);

    await page.goto('/plataforma/crm/pipeline', { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    await page.getByText('Abigail Monsalve').first().click();
    await expect(page.locator('body')).toContainText(/Modificar Etapa/i);

    await page.locator('button').filter({ hasText: 'POR LLAMAR' }).first().click();

    await expect.poll(() => pipeline.getReorderPayload()).not.toBeNull();
    await expect(pipeline.getReorderPayload()).toEqual([
      { id: 'lead-1', etapa_actual_id: 'stage-call' },
    ]);
  });
});
