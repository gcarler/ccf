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

const DAY_EVENTS: CalendarItem[] = [
  {
    id: 'ev-day-1',
    title: 'Reunión matutina',
    start: '2026-07-28T09:00:00.000Z',
    end: '2026-07-28T10:00:00.000Z',
    type: 'agenda_event',
    allDay: false,
    location: 'Sala B',
  },
  {
    id: 'ev-day-2',
    title: 'Taller de oración',
    start: '2026-07-28T14:00:00.000Z',
    end: '2026-07-28T16:00:00.000Z',
    type: 'agenda_event',
    allDay: false,
    location: 'Templo',
  },
];

async function installMocks(page: Page) {
  await page.clock.setFixedTime(new Date('2026-07-28T08:00:00.000Z'));
  await installMockPlatformSession(page, {
    role: 'admin',
    permissions: { 'spiritual_life:read': 'allow', 'spiritual_life:edit': 'allow' },
  });

  await page.route('**/api/system/calendar**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(DAY_EVENTS) });
  });

  await page.route('**/api/projects/_tasks**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ _tasks: [] }) });
  });
}

test.describe('Day view @agenda', () => {
  test('renders day view with time slots', async ({ page }) => {
    await installMocks(page);
    await page.goto('/plataforma/calendar');

    await page.click('button:has-text("Semana")');
    await page.click('button:has-text("Día")');

    await expect(page.getByRole('region', { name: 'Vista diaria', exact: true }).getByText('Reunión matutina', { exact: true })).toBeVisible({ timeout: 10000 });
    await expect(page.getByRole('region', { name: 'Vista diaria', exact: true }).getByText('Sala B', { exact: true })).toBeVisible();
  });

  test('shows multiple events in day timeline', async ({ page }) => {
    await installMocks(page);
    await page.goto('/plataforma/calendar');

    await page.click('button:has-text("Semana")');
    await page.click('button:has-text("Día")');

    await expect(page.getByRole('region', { name: 'Vista diaria', exact: true }).getByText('Reunión matutina', { exact: true })).toBeVisible({ timeout: 10000 });
    await expect(page.getByRole('region', { name: 'Vista diaria', exact: true }).getByText('Taller de oración', { exact: true })).toBeVisible();
  });

  test('day view shows event locations', async ({ page }) => {
    await installMocks(page);
    await page.goto('/plataforma/calendar');

    await page.click('button:has-text("Semana")');
    await page.click('button:has-text("Día")');

    await expect(page.getByRole('region', { name: 'Vista diaria', exact: true }).getByText('Templo', { exact: true })).toBeVisible({ timeout: 10000 });
  });
});
