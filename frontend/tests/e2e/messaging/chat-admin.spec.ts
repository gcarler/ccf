import { expect, test, type Page } from '@playwright/test';
import { installMockPlatformSession } from '../helpers/mockPlatformSession';
import type { ChatAdminMessageItem } from '@/types/directMessages';

const CURRENT_PERSONA_ID = 'e2e-persona';

function generateMockItems(count: number, startId = 0): ChatAdminMessageItem[] {
  return Array.from({ length: count }, (_, i) => {
    const id = startId + i;
    return {
      id: `msg-${id}`,
      conversation_id: `conv-${id % 5}`,
      conversation_name: `Conversación ${id % 5}`,
      sender_id: CURRENT_PERSONA_ID,
      sender_name: 'Usuario E2E',
      content: `Mensaje de prueba ${id}`,
      created_at: new Date(Date.now() - id * 60_000).toISOString(),
      is_read: true,
      attachment_type: null,
      attachment_name: null,
      attachment_url: null,
      attachment_size: null,
      reply_to_id: null,
      mentions: [],
    };
  });
}

const ITEMS_PAGE_1 = generateMockItems(50, 0);
const ITEMS_PAGE_2 = generateMockItems(5, 50);

async function installChatAdminMocks(page: Page) {
  await page.route('**/api/chat/my-messages*', async (route) => {
    const url = new URL(route.request().url());
    const offset = Number(url.searchParams.get('offset') ?? '0');
    await new Promise((resolve) => setTimeout(resolve, 100));

    if (offset >= 50) {
      await route.fulfill({ status: 200, json: ITEMS_PAGE_2 });
    } else {
      await route.fulfill({ status: 200, json: ITEMS_PAGE_1 });
    }
  });

  await page.route('**/api/chat/mentions*', async (route) => {
    const url = new URL(route.request().url());
    const offset = Number(url.searchParams.get('offset') ?? '0');
    await new Promise((resolve) => setTimeout(resolve, 100));

    if (offset >= 50) {
      await route.fulfill({ status: 200, json: ITEMS_PAGE_2 });
    } else {
      await route.fulfill({ status: 200, json: ITEMS_PAGE_1 });
    }
  });
}

test.describe('Chat admin center', () => {
  test.beforeEach(async ({ page }) => {
    await installMockPlatformSession(page, {
      role: 'admin',
      permissions: {
        'messaging:read': 'allow',
        'messaging:send': 'allow',
      },
    });

    await installChatAdminMocks(page);
    await page.emulateMedia({ reducedMotion: 'reduce' });
  });

  test('loads messages, shows loading state, and reveals load-more button with correct aria-label', async ({ page }) => {
    const consoleErrors: string[] = [];
    const allConsole: string[] = [];
    const apiErrors: { status: number; url: string }[] = [];

    page.on('console', (msg) => {
      allConsole.push(`[${msg.type()}] ${msg.text()}`);
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });

    page.on('response', (response) => {
      if (response.status() >= 400 && response.url().includes('/api/')) {
        apiErrors.push({ status: response.status(), url: response.url() });
      }
    });

    await page.goto('/plataforma/inbox/chat', { waitUntil: 'load' });

    // Initial loading state
    await expect(page.getByText('Cargando mensajes…')).toBeVisible();
    await expect(page.getByText('Cargando mensajes…')).toBeHidden();

    // First page loaded and rendered
    await expect(page.getByText('50 resultados')).toBeVisible();
    await expect(page.getByText('Mensaje de prueba 0')).toBeVisible();
    await expect(page.getByText('Mensaje de prueba 49')).toBeVisible();

    // Load-more button has the expected accessible label and is visible
    const loadMoreBtn = page.getByRole('button', { name: 'Cargar más mensajes' });
    await expect(loadMoreBtn).toBeVisible();
    await expect(loadMoreBtn).toHaveAttribute('aria-label', 'Cargar más mensajes');

    // Click load-more and verify loading-more state
    await loadMoreBtn.click();
    await expect(page.getByText('Cargando más…')).toBeVisible();
    await expect(page.getByText('Cargando más…')).toBeHidden();

    // Second page is appended
    await expect(page.getByText('55 resultados')).toBeVisible();
    await expect(page.getByText('Mensaje de prueba 50')).toBeVisible();

    // Button is hidden because the second page returned fewer than the page limit
    await expect(loadMoreBtn).toBeHidden();

    console.log('--- ALL CONSOLE MESSAGES ---');
    console.log(allConsole.join('\n'));
    console.log('--- END CONSOLE MESSAGES ---');

    expect(consoleErrors, 'No console errors expected').toEqual([]);
    expect(apiErrors, 'No API errors expected').toEqual([]);
  });

  test('switches to mentions tab and supports pagination', async ({ page }) => {
    await page.goto('/plataforma/inbox/chat', { waitUntil: 'load' });
    await expect(page.getByText('50 resultados')).toBeVisible();

    await page.getByRole('button', { name: /Menciones/i }).click();

    await expect(page.getByText('Cargando mensajes…')).toBeVisible();
    await expect(page.getByText('Cargando mensajes…')).toBeHidden();

    await expect(page.getByText('50 resultados')).toBeVisible();

    const loadMoreBtn = page.getByRole('button', { name: 'Cargar más mensajes' });
    await expect(loadMoreBtn).toBeVisible();

    await loadMoreBtn.click();
    await expect(page.getByText('Cargando más…')).toBeVisible();
    await expect(page.getByText('Cargando más…')).toBeHidden();

    await expect(page.getByText('55 resultados')).toBeVisible();
    await expect(loadMoreBtn).toBeHidden();
  });
});
