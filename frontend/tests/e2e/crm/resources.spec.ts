import { expect, test, type Page } from '@playwright/test';
import { installMockPlatformSession } from '../helpers/mockPlatformSession';

const CATEGORIES = [
  { id: 'cat-1', nombre: 'Seguimiento', color_ui_hex: '#2563eb' },
  { id: 'cat-2', nombre: 'Bienvenida', color_ui_hex: '#059669' },
];

const TEMPLATE = {
  id: 'tpl-1',
  titulo: 'Bienvenida nuevos',
  canal: 'EMAIL',
  asunto: 'Bienvenido a CCF',
  contenido_texto: 'Hola {{nombre}}, gracias por acompañarnos en {{sede}}.',
  contenido_html:
    '<table><tr><td><h1>Bienvenido a CCF</h1><p>Hola {{nombre}}, gracias por acompañarnos en {{sede}}.</p></td></tr></table>',
  variables_requeridas: ['nombre', 'sede'],
  total_envios: 12,
  fecha_creacion: '2026-07-10T00:00:00Z',
  categoria: CATEGORIES[1],
  adjuntos: [],
};

const BUILDER_TEMPLATE = {
  ...TEMPLATE,
  contenido_html: JSON.stringify([
    {
      id: 'block-header-1',
      type: 'header',
      props: {
        title: 'Bienvenido a CCF',
        subtitle: 'Nos alegra acompañarte',
        textAlign: 'center',
        titleColor: '#001B48',
      },
    },
  ]),
};

async function installResourcesMocks(page: Page) {
  let lastPatchBody: Record<string, unknown> | null = null;

  await installMockPlatformSession(page, {
    permissions: {
      'crm:read': 'allow',
      'crm:edit': 'allow',
      'crm:manage': 'allow',
    },
  });

  await page.route('**/api/crm/resources/categorias**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(CATEGORIES),
    });
  });

  await page.route('**/api/crm/resources/plantillas?**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([TEMPLATE]),
    });
  });

  await page.route('**/api/crm/resources/plantillas/tpl-1/bitacora', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 'log-1',
          estado: 'ENTREGADO',
          destinatario_id: 'persona-ana-garcia',
          fecha_envio: '2026-07-15T10:00:00Z',
          payload_hidratado: {},
        },
      ]),
    });
  });

  await page.route('**/api/crm/resources/plantillas/tpl-1', async (route) => {
    if (route.request().method() === 'PATCH') {
      lastPatchBody = route.request().postDataJSON() as Record<string, unknown>;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ...BUILDER_TEMPLATE, ...lastPatchBody }),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(BUILDER_TEMPLATE),
    });
  });

  return {
    getLastPatchBody: () => lastPatchBody,
  };
}

test.describe('CRM resources deep smoke', () => {
  test('renders template detail and history tabs with live contract shape', async ({ page }) => {
    await installResourcesMocks(page);

    await page.goto('/plataforma/crm/resources', { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    await expect(page.locator('body')).toContainText(/Bienvenida nuevos/i);
    await page.getByText('Bienvenida nuevos').first().click();

    await expect(page.locator('body')).toContainText(/Vista previa HTML/i);
    await expect(page.locator('body')).toContainText(/Adjuntos \(0\)/i);

    await page.getByRole('button', { name: /Historial/i }).click();
    await expect(page.locator('body')).toContainText(/Entregado/i);
    await expect(page.locator('body')).toContainText(/→ persona-/i);
  });

  test('loads the builder and persists template edits through the canonical endpoint', async ({ page }) => {
    const resources = await installResourcesMocks(page);

    await page.goto('/plataforma/crm/resources/builder/tpl-1', { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    const titleInput = page.locator('input[placeholder="Nombre de la plantilla"]').first();
    await expect(titleInput).toHaveValue('Bienvenida nuevos');
    await titleInput.fill('Bienvenida nuevos v2');
    await page.getByRole('button', { name: /Guardar/i }).click();

    await expect.poll(() => resources.getLastPatchBody()).not.toBeNull();
    await expect
      .poll(() => (resources.getLastPatchBody() as Record<string, unknown> | null)?.titulo)
      .toBe('Bienvenida nuevos v2');
  });
});
