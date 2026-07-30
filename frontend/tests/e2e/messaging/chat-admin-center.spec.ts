import { expect, test, type Page } from '@playwright/test';
import { installMockPlatformSession } from '../helpers/mockPlatformSession';

const SENT_MESSAGES = [
  {
    id: 'msg-sent-1',
    conversation_id: 'conv-1',
    conversation_name: 'Abigail Monsalve',
    sender_id: 'e2e-user',
    sender_name: 'pastor.e2e',
    content: 'Nos vemos en el seguimiento de esta tarde.',
    created_at: '2026-07-16T08:58:00Z',
    is_read: true,
    attachment_url: null,
    attachment_type: null,
    attachment_name: null,
    attachment_size: null,
    reply_to_id: null,
    mentions: [],
  },
  {
    id: 'msg-sent-2',
    conversation_id: 'conv-2',
    conversation_name: 'Carlos Rueda',
    sender_id: 'e2e-user',
    sender_name: 'pastor.e2e',
    content: 'Te compartí el recurso de liderazgo.',
    created_at: '2026-07-16T07:20:00Z',
    is_read: true,
    attachment_url: '/static/chat_attachments/file.pdf',
    attachment_type: 'pdf',
    attachment_name: 'liderazgo.pdf',
    attachment_size: 1024,
    reply_to_id: null,
    mentions: [],
  },
];

const MENTIONS = [
  {
    id: 'msg-mention-1',
    conversation_id: 'conv-1',
    conversation_name: 'Abigail Monsalve',
    sender_id: 'persona-abigail',
    sender_name: 'Abigail Monsalve',
    content: '@pastor.e2e ¿ya quedó lista la reunión?',
    created_at: '2026-07-16T09:15:00Z',
    is_read: false,
    attachment_url: null,
    attachment_type: null,
    attachment_name: null,
    attachment_size: null,
    reply_to_id: null,
    mentions: ['e2e-user'],
  },
];

async function installChatAdminMocks(page: Page) {
  await installMockPlatformSession(page, {
    role: 'admin',
    permissions: {
      'messaging:read': 'allow',
      'messaging:edit': 'allow',
    },
  });

  await page.route('**/api/chat/my-messages**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(SENT_MESSAGES),
    });
  });

  await page.route('**/api/chat/mentions**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MENTIONS),
    });
  });
}

test.describe('Chat admin center', () => {
  test.beforeEach(async ({ page }) => {
    await installChatAdminMocks(page);
  });

  test('renders sent messages and supports tab switching', async ({ page }) => {
    await page.goto('/plataforma/inbox/chat', { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    await expect(page.locator('body')).toContainText('Centro de mensajes');
    await expect(page.locator('body')).toContainText('Mis mensajes');
    await expect(page.locator('body')).toContainText('Menciones');

    await expect(page.locator('body')).toContainText('Nos vemos en el seguimiento');
    await expect(page.locator('body')).toContainText('Abigail Monsalve');
    await expect(page.locator('body')).toContainText('Carlos Rueda');
    await expect(page.locator('body')).toContainText('liderazgo.pdf');

    await page.getByRole('button', { name: /Menciones/i }).click();
    await expect(page.locator('body')).toContainText('@pastor.e2e ¿ya quedó lista la reunión?');
    await expect(page.locator('body')).toContainText('Nuevo');
  });

  test('filters results by search term', async ({ page }) => {
    await page.goto('/plataforma/inbox/chat', { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    await page.getByPlaceholder(/Buscar/i).fill('Carlos');
    await expect(page.locator('body')).toContainText('Carlos Rueda');
    await expect(page.locator('body')).not.toContainText('Abigail Monsalve');

    await page.getByPlaceholder(/Buscar/i).fill('reunión');
    await expect(page.locator('body')).not.toContainText('Carlos Rueda');
    await expect(page.locator('body')).not.toContainText('Abigail Monsalve');

    await page.getByRole('button', { name: /Menciones/i }).click();
    await page.getByPlaceholder(/Buscar/i).fill('reunión');
    await expect(page.locator('body')).toContainText('@pastor.e2e ¿ya quedó lista la reunión?');
  });

  test('navigates to the conversation when an item is clicked', async ({ page }) => {
    await page.goto('/plataforma/inbox/chat', { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    const link = page.locator(`a[href="/plataforma/messages?conv=${SENT_MESSAGES[0].conversation_id}"]`).first();
    await expect(link).toBeVisible();
    await link.click();

    await expect(page).toHaveURL(/\/plataforma\/messages\?conv=conv-1/);
  });
});
