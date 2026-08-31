import { expect, test, type Page } from '@playwright/test';
import { installMockPlatformSession } from '../helpers/mockPlatformSession';

const SITE_KEY = 'ccf';
const PAGE_SLUG = 'home';

const INITIAL_SECTIONS = [
  {
    id: 'section-hero-1',
    page_id: 'page-home-1',
    section_key: 'hero-1',
    type: 'hero',
    props_json: {
      title: 'Título Hero Inicial',
      body: 'Descripción inicial del héroe',
      cta_label: 'Comenzar',
      cta_href: '/inicio',
      bg_image: '',
    },
    sort_order: 1,
    is_visible: true,
    status: 'active',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
];

const THEME_FIXTURE = {
  id: 'theme-1',
  site_id: 'site-ccf',
  name: 'Tema Faro',
  tokens_json: {
    '--site-background': '#001134',
    '--site-primary': '#018abd',
  },
  is_active: true,
  status: 'active',
};

const MEDIA_FIXTURE = {
  items: [
    {
      id: '1',
      title: 'Foto 1',
      url: 'https://images.unsplash.com/photo-1500.jpg',
      key: 'photo-1',
      mimetype: 'image/jpeg',
      mime_type: 'image/jpeg',
      size: 1024,
      created_at: '2026-01-01',
    },
  ],
  total: 1,
};

async function setupPuckBuilderMocks(page: Page) {
  await page.unrouteAll({ behavior: 'ignoreErrors' });

  await installMockPlatformSession(page, {
    role: 'admin',
    permissions: { 'cms:read': 'allow', 'cms:edit': 'allow', 'cms:manage': 'allow' },
  });

  // Mock initial sections list
  await page.route(`**/cms/v2/sites/${SITE_KEY}/pages/${PAGE_SLUG}/sections**`, async (route) => {
    const method = route.request().method();
    if (method === 'POST') {
      const body = route.request().postDataJSON() as Record<string, unknown>;
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'section-new-1',
          type: body.type || 'hero',
          props_json: body.props_json || {},
          sort_order: 1,
          is_visible: true,
        }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(INITIAL_SECTIONS),
    });
  });

  // Mock section PATCH / update
  await page.route(`**/cms/v2/sites/${SITE_KEY}/pages/${PAGE_SLUG}/sections/*`, async (route) => {
    const method = route.request().method();
    if (method === 'PATCH' || method === 'PUT') {
      const body = route.request().postDataJSON() as Record<string, unknown>;
      const sectionId = route.request().url().split('/sections/')[1] || 'section-hero-1';
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: sectionId,
          type: 'hero',
          props_json: body.props_json || {},
          sort_order: 1,
          is_visible: true,
        }),
      });
      return;
    }
    await route.fallback();
  });

  // Mock theme endpoint
  await page.route(`**/cms/v2/public/sites/${SITE_KEY}/theme**`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(THEME_FIXTURE),
    });
  });

  // Mock CMS media endpoint
  await page.route('**/cms/media**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MEDIA_FIXTURE),
    });
  });

  // Mock AI text generation endpoint
  await page.route('**/system/ai/generate**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ response: 'Encuentro de Jóvenes CCF 2026' }),
    });
  });

  // Mock layout and configuration endpoints to prevent 401 redirects
  await page.route('**/workspace/config**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({}) });
  });

  await page.route('**/cms/v2/sites**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });

  await page.route('**/cms/v2/sites/ccf/themes**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });
}

test.describe('Puck Builder Visual Editor Flow', () => {
  test.beforeEach(async ({ page }) => {
    page.on('console', msg => console.log('PAGE LOG:', msg.text()));
    page.on('pageerror', err => console.log('PAGE ERROR:', err.message));
    page.on('requestfailed', req => console.log('REQUEST FAILED:', req.url(), req.failure()?.errorText));
    await setupPuckBuilderMocks(page);
  });

  test('loads staging builder route /builder-puck with header elements', async ({ page }) => {
    await page.goto(`/plataforma/cms/builder-puck?site=${SITE_KEY}&page=${PAGE_SLUG}`, { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    // Verify main editor landmark
    await expect(page.getByRole('main', { name: 'Editor visual Puck' })).toBeVisible();

    // Verify header title and status badge
    await expect(page.getByText('Editando página: /home')).toBeVisible();
    await expect(page.getByText('Guardado en borrador')).toBeVisible();
  });

  test('loads main migrated builder route /builder with header elements', async ({ page }) => {
    await page.goto(`/plataforma/cms/builder?site=${SITE_KEY}&page=${PAGE_SLUG}`, { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    // Verify main editor landmark
    await expect(page.getByRole('main', { name: 'Editor visual Puck' })).toBeVisible();

    // Verify header title and status badge
    await expect(page.getByText('Editando página: /home')).toBeVisible();
    await expect(page.getByText('Guardado en borrador')).toBeVisible();
  });

  test('selects and edits Hero section with MediaPicker, AI text assistant, and save flow', async ({ page }) => {
    await page.goto(`/plataforma/cms/builder-puck?site=${SITE_KEY}&page=${PAGE_SLUG}`, { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    // Verify main editor landmark and wait for Puck client hydration
    await expect(page.getByRole('main', { name: 'Editor visual Puck' })).toBeVisible();
    const heroHeading = page.getByRole('heading', { name: 'Título Hero Inicial' });
    await expect(heroHeading).toBeVisible({ timeout: 15000 });
    await page.waitForTimeout(2000);

    // Click on the hero section in the Puck canvas to reveal its fields in the sidebar
    await heroHeading.click();

    // ── MediaPicker Flow ──
    // Click "Seleccionar Imagen" button in MediaPickerField
    const selectImageBtn = page.getByRole('button', { name: 'Seleccionar Imagen' });
    await expect(selectImageBtn).toBeVisible();
    await selectImageBtn.click();

    // Verify MediaPicker dialog opens
    const mediaPickerModal = page.getByTestId('media-picker');
    await expect(mediaPickerModal).toBeVisible();

    // Click on the media item button inside drawer
    const mediaItemBtn = page.getByTestId('media-item-button').first();
    await expect(mediaItemBtn).toBeVisible();
    await mediaItemBtn.click();

    // Verify MediaPicker dialog closes and image field updates
    await expect(mediaPickerModal).not.toBeVisible();
    await expect(page.getByRole('button', { name: 'Cambiar Imagen' })).toBeVisible({ timeout: 15000 });

    // ── AI Text Generation Flow ──
    // Use prompt chip "+ Título atractivo" or fill prompt input and click "Redactar IA"
    const aiChipBtn = page.getByRole('button', { name: '+ Título atractivo' });
    await expect(aiChipBtn).toBeVisible();
    await aiChipBtn.click();

    // Verify heading in canvas or input value updates with AI generated text
    await expect(page.getByRole('heading', { name: 'Encuentro de Jóvenes CCF 2026' })).toBeVisible();

    // ── Auto-Save and Manual Save Flow ──
    // Verify status badge updated (transitioned through "Sin guardar", "Guardando cambios...", "Guardado en borrador")
    // Click manual "Guardar" button to force immediate sync if not already saved
    const saveBtn = page.getByRole('button', { name: 'Guardar' });
    await expect(saveBtn).toBeVisible();
    await saveBtn.click();

    // Verify final state status badge is "Guardado en borrador"
    await expect(page.getByText('Guardado en borrador')).toBeVisible();
  });
});
