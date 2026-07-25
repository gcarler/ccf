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

const SEARCH_EVENTS: CalendarItem[] = [
  {
    id: 'ev-search-1',
    title: 'Conferencia de líderes',
    start: '2026-07-28T10:00:00.000Z',
    end: '2026-07-28T12:00:00.000Z',
    type: 'agenda_event',
    allDay: false,
    location: 'Sala A',
  },
  {
    id: 'ev-search-2',
    title: 'Retiro juvenil',
    start: '2026-07-29T08:00:00.000Z',
    end: '2026-07-29T18:00:00.000Z',
    type: 'agenda_event',
    allDay: false,
    location: 'Montaña',
  },
];

async function installMocks(page: Page) {
  await installMockPlatformSession(page, {
    role: 'admin',
    permissions: { 'spiritual_life:read': 'allow', 'spiritual_life:edit': 'allow' },
  });

  await page.route('**/api/system/calendar**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(SEARCH_EVENTS) });
  });

  await page.route('**/api/projects/_tasks**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ _tasks: [] }) });
  });
}

test.describe('Search bar @agenda', () => {
  test('displays search input', async ({ page }) => {
    await installMocks(page);
    await page.goto('/plataforma/calendar');

    const searchInput = page.locator('input[placeholder*="Buscar"]');
    await expect(searchInput).toBeVisible({ timeout: 10000 });
  });

  test('search input is focusable', async ({ page }) => {
    await installMocks(page);
    await page.goto('/plataforma/calendar');

    const searchInput = page.locator('input[placeholder*="Buscar"]');
    await searchInput.click();
    await expect(searchInput).toBeFocused();
  });

  test('search input accepts text', async ({ page }) => {
    await installMocks(page);
    await page.goto('/plataforma/calendar');

    const searchInput = page.locator('input[placeholder*="Buscar"]');
    await searchInput.fill('Conferencia');
    await expect(searchInput).toHaveValue('Conferencia');
  });
});
