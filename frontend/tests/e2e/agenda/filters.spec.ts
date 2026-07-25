import { expect, test, type Page } from '@playwright/test';
import { installMockPlatformSession } from '../helpers/mockPlatformSession';

type CalendarItem = {
  id: string;
  title: string;
  start: string;
  end: string;
  type: string;
  allDay: boolean;
  href?: string;
  location?: string;
};

const MIXED_EVENTS: CalendarItem[] = [
  {
    id: 'agenda-601',
    title: 'Servicio dominical',
    start: '2026-07-27T10:00:00.000Z',
    end: '2026-07-27T12:00:00.000Z',
    type: 'agenda_event',
    allDay: false,
    location: 'Templo principal',
  },
  {
    id: 'evangelism-601',
    title: 'Campaña evangelística',
    start: '2026-07-28T18:00:00.000Z',
    end: '2026-07-28T20:00:00.000Z',
    type: 'evangelism_event',
    allDay: false,
    location: 'Parque central',
  },
  {
    id: 'task-601',
    title: 'Preparar materiales',
    start: '2026-07-29T09:00:00.000Z',
    end: '2026-07-29T10:00:00.000Z',
    type: 'task',
    allDay: false,
  },
];

async function installFilterMocks(page: Page) {
  await installMockPlatformSession(page, {
    role: 'admin',
    permissions: { 'spiritual_life:read': 'allow', 'spiritual_life:edit': 'allow' },
  });

  await page.route('**/api/system/calendar**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MIXED_EVENTS) });
  });

  await page.route('**/api/projects/_tasks**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ _tasks: [] }) });
  });
}

test.describe('Event type filters @agenda', () => {
  test('shows all event types in the filter panel', async ({ page }) => {
    await installFilterMocks(page);
    await page.goto('/plataforma/calendar');

    await expect(page.locator('text=Filtrar por tipo')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=Agenda')).toBeVisible();
    await expect(page.locator('text=Evento')).toBeVisible();
  });

  test('displays event counts per type', async ({ page }) => {
    await installFilterMocks(page);
    await page.goto('/plataforma/calendar');

    await expect(page.locator('text=Filtrar por tipo')).toBeVisible({ timeout: 10000 });
    const agendaChip = page.locator('button:has-text("Agenda")');
    await expect(agendaChip).toBeVisible();
  });

  test('toggle filter hides/shows events', async ({ page }) => {
    await installFilterMocks(page);
    await page.goto('/plataforma/calendar');

    await expect(page.locator('text=Servicio dominical')).toBeVisible({ timeout: 10000 });

    const agendaFilter = page.locator('button:has-text("Agenda")').first();
    await agendaFilter.click();

    await expect(page.locator('text=Servicio dominical')).not.toBeVisible({ timeout: 5000 });

    await agendaFilter.click();
    await expect(page.locator('text=Servicio dominical')).toBeVisible({ timeout: 5000 });
  });
});
