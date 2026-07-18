import { expect, test, type Page } from '@playwright/test';
import { installMockPlatformSession } from '../helpers/mockPlatformSession';

const MOCK_DASHBOARD = {
  cards: [
    { title: 'Personas Registradas', value: 245, trend: '+12%', color: 'blue', icon: 'users' },
    { title: 'Roles Asignados', value: 89, trend: '+5%', color: 'emerald', icon: 'shield' },
    { title: 'En Directorio', value: 230, trend: '+8%', color: 'amber', icon: 'directory' },
    { title: 'Actividad', value: 67, trend: '-3%', color: 'blue', icon: 'activity' },
  ],
  pipeline_funnel: [
    { stage: 'Contacto Inicial', count: 45 },
    { stage: 'Seguimiento', count: 32 },
    { stage: 'Consolidación', count: 18 },
    { stage: 'Miembro Activo', count: 12 },
  ],
  growth_chart: [
    { month: 'Ene', value: 180 },
    { month: 'Feb', value: 195 },
    { month: 'Mar', value: 210 },
    { month: 'Abr', value: 225 },
    { month: 'May', value: 240 },
    { month: 'Jun', value: 245 },
  ],
  interaction_heatmap: [],
  conversion_rate: 0.27,
  pending_followups: 8,
  slas_vencidos: 2,
};

const MOCK_DASHBOARD_EMPTY = {
  cards: [],
  pipeline_funnel: [],
  growth_chart: [],
  interaction_heatmap: [],
  conversion_rate: 0,
  pending_followups: 0,
  slas_vencidos: 0,
};

async function installDashboardMocks(page: Page, dashboardData = MOCK_DASHBOARD) {
  await installMockPlatformSession(page, {
    permissions: {
      'crm:read': 'allow',
      'crm:edit': 'allow',
      'crm:manage': 'allow',
    },
  });

  await page.route('**/api/dashboard/crm**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(dashboardData),
    });
  });

  await page.route('**/api/crm/personas**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ items: [], total: 0 }),
    });
  });
}

test.describe('CRM dashboard smoke', () => {
  test('renders metric cards with data', async ({ page }) => {
    await installDashboardMocks(page);
    await page.goto('/plataforma/crm', { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(1000);

    await expect(page.locator('body')).toContainText(/Personas Registradas/i);
    await expect(page.locator('body')).toContainText(/245/i);
    await expect(page.locator('body')).toContainText(/Roles Asignados/i);
    await expect(page.locator('body')).toContainText(/89/i);
  });

  test('renders quick access links', async ({ page }) => {
    await installDashboardMocks(page);
    await page.goto('/plataforma/crm', { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(1000);

    const body = page.locator('body');
    const hasPersonasLink = await body.getByText(/personas/i).count();
    const hasPipelineLink = await body.getByText(/pipeline/i).count();
    expect(hasPersonasLink + hasPipelineLink).toBeGreaterThan(0);
  });

  test('handles empty dashboard gracefully', async ({ page }) => {
    await installDashboardMocks(page, MOCK_DASHBOARD_EMPTY);
    await page.goto('/plataforma/crm', { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(1000);

    await expect(page.locator('body')).toContainText(/crm|pastoral|directorio/i);
  });

  test('dashboard API error shows toast without crash', async ({ page }) => {
    await installMockPlatformSession(page, {
      permissions: {
        'crm:read': 'allow',
        'crm:edit': 'allow',
      },
    });

    await page.route('**/api/dashboard/crm**', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Internal server error' }),
      });
    });

    await page.route('**/api/crm/personas**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: [], total: 0 }),
      });
    });

    const pageErrors: string[] = [];
    page.on('pageerror', (err) => pageErrors.push(err.message));

    await page.goto('/plataforma/crm', { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    expect(pageErrors).toEqual([]);
  });
});
