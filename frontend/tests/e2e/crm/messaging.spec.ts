import { expect, test, type Page } from '@playwright/test';
import { installMockPlatformSession } from '../helpers/mockPlatformSession';

const HISTORY_ROWS = [
  {
    id: 'msg-1',
    name: 'Invitación Asamblea',
    campaign_name: 'Invitación Asamblea',
    channel: 'whatsapp',
    status: 'sent',
    target_count: 24,
    delivered_count: 24,
    failed_count: 0,
    sent_at: '2026-07-17T14:30:00Z',
  },
  {
    id: 'msg-2',
    name: 'Seguimiento Mentoría',
    campaign_name: 'Seguimiento Mentoría',
    channel: 'email',
    status: 'failed',
    target_count: 8,
    delivered_count: 0,
    failed_count: 8,
    sent_at: '2026-07-16T12:00:00Z',
  },
];

const DETAIL_ROW = {
  id: 'msg-1',
  name: 'Invitación Asamblea',
  campaign_name: 'Invitación Asamblea',
  channel: 'whatsapp',
  status: 'sent',
  sent_at: '2026-07-17T14:30:00Z',
  target_count: 24,
  delivered_count: 24,
  failed_count: 0,
  content: 'Hola {nombre}, te esperamos este domingo en la asamblea general.',
  external_id: 'wa-campaign-001',
};

async function installMessagingMocks(page: Page) {
  let sendPayload: Record<string, unknown> | null = null;

  await installMockPlatformSession(page, {
    permissions: {
      'crm:read': 'allow',
      'crm:edit': 'allow',
      'crm:manage': 'allow',
    },
  });

  await page.addInitScript(() => {
    localStorage.setItem('crm_messaging_view', 'table');
  });

  await page.route('**/api/crm/messaging/history', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(HISTORY_ROWS),
    });
  });

  await page.route('**/api/crm/messaging/history/msg-1', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(DETAIL_ROW),
    });
  });

  await page.route('**/api/crm/messaging/send', async (route) => {
    sendPayload = route.request().postDataJSON() as Record<string, unknown>;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ ok: true, id: 'send-1' }),
    });
  });

  return {
    getSendPayload: () => sendPayload,
  };
}

test.describe('CRM messaging deep smoke', () => {
  test('renders history and drills into campaign detail', async ({ page }) => {
    await installMessagingMocks(page);

    await page.goto('/plataforma/crm/messaging', { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    await expect(page.locator('body')).toContainText(/Centro de Mensajería/i);
    await expect(page.locator('body')).toContainText(/Invitación Asamblea/i);
    await expect(page.locator('body')).toContainText(/Seguimiento Mentoría/i);

    await page.goto('/plataforma/crm/messaging/msg-1', { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    await expect(page.locator('body')).toContainText(/Contenido del Mensaje/i);
    await expect(page.locator('body')).toContainText(/Destinatarios/i);
    await expect(page.locator('body')).toContainText(/24/i);
    await expect(page.locator('body')).toContainText(/Estado de Entrega/i);
    await expect(page.locator('body')).toContainText(/Completado/i);
  });

  test('submits a messaging campaign with the current CRM contract', async ({ page }) => {
    const messaging = await installMessagingMocks(page);

    await page.addInitScript(() => {
      localStorage.setItem('crm_messaging_view', 'grid');
    });

    await page.goto('/plataforma/crm/messaging', { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    await page.getByPlaceholder(/Invitación Asamblea de Personas/i).fill('Campaña CRM Julio');
    await page.getByPlaceholder(/Hola \{nombre\}/i).fill('Hola {nombre}, recuerda tu seguimiento pastoral.');
    await page.getByText(/Personas Activos/i).click();
    await page.getByRole('button', { name: /Lanzar Campaña/i }).click();

    await expect.poll(() => messaging.getSendPayload()).not.toBeNull();
    await expect
      .poll(() => (messaging.getSendPayload() as Record<string, unknown> | null)?.campaign_name)
      .toBe('Campaña CRM Julio');
    await expect
      .poll(() => (messaging.getSendPayload() as Record<string, unknown> | null)?.target_segments)
      .toEqual(['active']);
  });
});
