import { expect, test, type Page } from '@playwright/test';
import { installMockPlatformSession } from '../helpers/mockPlatformSession';

const MOCK_GRUPOS = [
  {
    id: 'grupo-1',
    name: 'Faro Norte',
    personas_count: 12,
    total_personas: 15,
    leader_name: 'Ana García',
    meeting_day: 'Miércoles',
    meeting_time: '19:00',
  },
  {
    id: 'grupo-2',
    name: 'Faro Sur',
    personas_count: 8,
    total_personas: 10,
    leader_name: 'Carlos López',
    meeting_day: 'Jueves',
    meeting_time: '18:30',
  },
];

const MOCK_SEASONS = [
  { id: 'season-1', name: '2026-Q3', status: 'active' },
  { id: 'season-2', name: '2026-Q2', status: 'closed' },
];

const MOCK_GRUPO_DETAIL = {
  id: 'grupo-1',
  name: 'Faro Norte',
  base_attendees: [
    { persona_id: 'p1', name: 'Ana García' },
    { persona_id: 'p2', name: 'Luis Martínez' },
    { persona_id: 'p3', name: 'María Rodríguez' },
  ],
  leader_id: 'leader-1',
  assistant_id: 'assistant-1',
  host_id: 'host-1',
};

async function installGroupsAdminMocks(page: Page) {
  let sessionPayload: Record<string, unknown> | null = null;
  let attendancePayload: Record<string, unknown> | null = null;

  await installMockPlatformSession(page, {
    permissions: {
      'crm:read': 'allow',
      'crm:edit': 'allow',
      'crm:manage': 'allow',
    },
  });

  await page.route('**/api/community/grupos**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_GRUPOS),
    });
  });

  await page.route('**/api/evangelism/groups/seasons**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_SEASONS),
    });
  });

  await page.route('**/api/evangelism/grupos/grupo-1**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_GRUPO_DETAIL),
    });
  });

  await page.route('**/api/evangelism/groups/sessions**', async (route) => {
    if (route.request().method() === 'POST') {
      sessionPayload = route.request().postDataJSON() as Record<string, unknown>;
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({ id: 'session-new', ok: true }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    });
  });

  await page.route('**/api/evangelism/groups/sessions/*/attendance**', async (route) => {
    attendancePayload = route.request().postDataJSON() as Record<string, unknown>;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ ok: true }),
    });
  });

  return {
    getSessionPayload: () => sessionPayload,
    getAttendancePayload: () => attendancePayload,
  };
}

test.describe('CRM groups admin bridge smoke', () => {
  test.beforeEach(async ({ page }) => {
    await installGroupsAdminMocks(page);
  });

  test('loads groups admin page with group list', async ({ page }) => {
    await page.goto('/plataforma/crm/groups/admin', { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    await expect(page.locator('body')).toContainText(/Faro Norte/i);
    await expect(page.locator('body')).toContainText(/Faro Sur/i);
  });

  test('shows group details when selecting a group', async ({ page }) => {
    await page.goto('/plataforma/crm/groups/admin', { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    const groupCard = page.locator('body').getByText('Faro Norte').first();
    await groupCard.click();
    await page.waitForTimeout(500);

    await expect(page.locator('body')).toContainText(/Ana García|Luis Martínez|María Rodríguez/i);
  });

  test('handles evangelism API errors gracefully', async ({ page }) => {
    await page.unroute('**/api/evangelism/groups/seasons**');
    await page.route('**/api/evangelism/groups/seasons**', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Internal server error' }),
      });
    });

    await page.goto('/plataforma/crm/groups/admin', { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    await page.waitForTimeout(1000);
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));
    expect(errors).toEqual([]);
  });

  test('submits the weekly report through the canonical evangelism bridge', async ({ page }) => {
    const bridge = await installGroupsAdminMocks(page);

    await page.goto('/plataforma/crm/groups/admin', { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    await page.getByText('Faro Norte').first().click();
    await expect(page.locator('body')).toContainText(/Ana García/i);

    await page.getByRole('button', { name: /Enviar Reporte Semanal/i }).click();

    await expect.poll(() => bridge.getSessionPayload()).not.toBeNull();
    await expect(bridge.getSessionPayload()).toMatchObject({
      season_id: 'season-1',
      grupo_id: 'grupo-1',
    });
    await expect.poll(() => bridge.getAttendancePayload()).not.toBeNull();
    await expect(bridge.getAttendancePayload()).toEqual({
      persona_ids: ['p1', 'p2', 'p3'],
    });
  });
});
