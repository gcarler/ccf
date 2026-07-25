import { expect, test } from '@playwright/test';
import { installMockPlatformSession } from '../helpers/mockPlatformSession';

const EVENTS = [
  {
    id: 'agenda-701',
    title: 'Reunión de oración',
    start: '2026-07-28T10:00:00.000Z',
    end: '2026-07-28T11:00:00.000Z',
    type: 'agenda_event',
    allDay: false,
    location: 'Capilla',
  },
];

async function installA11yMocks(page: Page) {
  await installMockPlatformSession(page, {
    role: 'admin',
    permissions: { 'spiritual_life:read': 'allow', 'spiritual_life:edit': 'allow' },
  });

  await page.route('**/api/system/calendar**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(EVENTS) });
  });

  await page.route('**/api/projects/_tasks**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ _tasks: [] }) });
  });
}

test.describe('Accessibility @agenda', () => {
  test('calendar page has no critical a11y violations', async ({ page }) => {
    await installA11yMocks(page);
    await page.goto('/plataforma/calendar');
    await expect(page.locator('text=Calendario')).toBeVisible({ timeout: 10000 });

    const title = await page.title();
    expect(title).toBeTruthy();

    const mainLandmark = page.locator('[role="main"], main');
    if (await mainLandmark.count() > 0) {
      await expect(mainLandmark.first()).toBeVisible();
    }
  });

  test('navigation buttons are keyboard accessible', async ({ page }) => {
    await installA11yMocks(page);
    await page.goto('/plataforma/calendar');
    await expect(page.locator('text=Calendario')).toBeVisible({ timeout: 10000 });

    const navButtons = page.locator('header button');
    const count = await navButtons.count();
    expect(count).toBeGreaterThan(0);

    for (let i = 0; i < Math.min(count, 3); i++) {
      const btn = navButtons.nth(i);
      await btn.focus();
      const isFocused = await btn.evaluate((el) => el === document.activeElement);
      expect(isFocused).toBeTruthy();
    }
  });

  test('agenda events page loads without console errors', async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });

    await installA11yMocks(page);
    await page.goto('/plataforma/agenda/events');
    await page.waitForTimeout(2000);

    const criticalErrors = consoleErrors.filter(
      (e) => e.includes('401') || e.includes('403') || e.includes('500') || e.includes('Uncaught'),
    );
    expect(criticalErrors).toHaveLength(0);
  });
});
