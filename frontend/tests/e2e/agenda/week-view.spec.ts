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

const MOCK_EVENTS: CalendarItem[] = [
  {
    id: 'agenda-501',
    title: 'Reunión de equipo',
    start: '2026-07-28T10:00:00.000Z',
    end: '2026-07-28T11:30:00.000Z',
    type: 'agenda_event',
    allDay: false,
    href: '/plataforma/agenda/events/501',
    location: 'Sala A',
  },
  {
    id: 'agenda-502',
    title: 'Retiro espiritual',
    start: '2026-07-29T00:00:00.000Z',
    end: '2026-07-29T23:59:59.000Z',
    type: 'agenda_event',
    allDay: true,
    href: '/plataforma/agenda/events/502',
    location: 'Monasterio',
  },
];

async function installWeekMocks(page: Page) {
  await installMockPlatformSession(page, {
    role: 'admin',
    permissions: { 'spiritual_life:read': 'allow', 'spiritual_life:edit': 'allow' },
  });

  await page.route('**/api/system/calendar**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_EVENTS) });
  });

  await page.route('**/api/projects/_tasks**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ _tasks: [] }) });
  });
}

test.describe('Week view @agenda', () => {
  test('renders week grid with day headers', async ({ page }) => {
    await installWeekMocks(page);
    await page.goto('/plataforma/calendar');

    await expect(page.locator('text=Semana')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=Lun')).toBeVisible();
    await expect(page.locator('text=Mar')).toBeVisible();
    await expect(page.locator('text=Todo el día')).toBeVisible();
  });

  test('shows timed events in the grid', async ({ page }) => {
    await installWeekMocks(page);
    await page.goto('/plataforma/calendar');

    await expect(page.locator('text=Reunión de equipo')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=Sala A')).toBeVisible();
  });

  test('shows all-day events in the all-day row', async ({ page }) => {
    await installWeekMocks(page);
    await page.goto('/plataforma/calendar');

    await expect(page.locator('text=Retiro espiritual').first()).toBeVisible({ timeout: 10000 });
  });

  test('switches to day view', async ({ page }) => {
    await installWeekMocks(page);
    await page.goto('/plataforma/calendar');

    await page.click('button:has-text("Semana")');
    await page.click('button:has-text("Día")');

    await expect(page.locator('text=Reunión de equipo')).toBeVisible({ timeout: 10000 });
  });
});
