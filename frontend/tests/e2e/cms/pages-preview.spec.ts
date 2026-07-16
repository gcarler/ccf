import { expect, test, type Page } from '@playwright/test';
import { installMockPlatformSession } from '../helpers/mockPlatformSession';

const SITE_KEY = 'faro';

const SITES_FIXTURE = [
  {
    id: 'site-1',
    site_key: SITE_KEY,
    name: 'Faro Global',
    base_path: '/',
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-07-10T00:00:00Z',
  },
];

const PAGES_FIXTURE = [
  {
    id: 'page-1',
    site_id: 'site-1',
    slug: 'bienvenida',
    title: 'Página de Bienvenida',
    status: 'published',
    seo_json: {
      meta_description: 'Landing principal de Faro.',
      canonical_url: 'https://faro.ccf.local/bienvenida',
    },
    published_version_id: 'version-1',
    publish_at: '2026-07-18T14:00:00Z',
    expires_at: null,
    created_at: '2026-07-01T12:00:00Z',
    updated_at: '2026-07-12T09:00:00Z',
  },
  {
    id: 'page-2',
    site_id: 'site-1',
    slug: 'retiro-jovenes',
    title: 'Retiro de Jóvenes',
    status: 'draft',
    seo_json: {
      meta_description: 'Evento de retiro juvenil.',
    },
    published_version_id: null,
    publish_at: null,
    expires_at: null,
    created_at: '2026-07-03T12:00:00Z',
    updated_at: '2026-07-11T09:00:00Z',
  },
  {
    id: 'page-3',
    site_id: 'site-1',
    slug: 'campamento-familias',
    title: 'Campamento de Familias',
    status: 'archived',
    seo_json: {},
    published_version_id: 'version-3',
    publish_at: null,
    expires_at: '2026-07-19T14:00:00Z',
    created_at: '2026-06-20T12:00:00Z',
    updated_at: '2026-07-09T09:00:00Z',
  },
];

const PREVIEW_FIXTURE = {
  site_key: SITE_KEY,
  slug: 'bienvenida',
  title: 'Página de Bienvenida',
  seo_json: {
    meta_description: 'Landing principal de Faro.',
  },
  canonical_url: 'https://faro.ccf.local/bienvenida',
  sections: [
    {
      id: 'section-hero',
      page_id: 'page-1',
      section_key: 'hero',
      type: 'hero',
      props_json: {
        eyebrow: 'Banner',
        title: 'Bienvenidos a Faro',
        description: 'Una comunidad para crecer en fe.',
        primaryCta: {
          label: 'Ver grupos',
          href: '/grupos',
        },
      },
      sort_order: 1,
      is_visible: true,
      status: 'active',
      created_at: '2026-07-01T12:00:00Z',
      updated_at: '2026-07-10T12:00:00Z',
    },
    {
      id: 'section-hidden',
      page_id: 'page-1',
      section_key: 'hidden',
      type: 'text',
      props_json: {
        title: 'No debe verse',
      },
      sort_order: 2,
      is_visible: false,
      status: 'active',
      created_at: '2026-07-01T12:00:00Z',
      updated_at: '2026-07-10T12:00:00Z',
    },
  ],
};

const THEME_FIXTURE = {
  id: 'theme-1',
  site_id: 'site-1',
  name: 'Tema Faro',
  tokens_json: {
    '--site-background': '#f6f7fb',
    '--site-primary': '#0f4c81',
    '--site-secondary': '#d19a2a',
  },
  is_active: true,
  status: 'active',
  version: 3,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-07-01T00:00:00Z',
};

async function installCmsDeepMocks(page: Page) {
  let pagesState = PAGES_FIXTURE.map((pageItem) => ({ ...pageItem, seo_json: { ...pageItem.seo_json } }));

  await installMockPlatformSession(page, {
    role: 'admin',
    permissions: {
      'cms:read': 'allow',
      'cms:edit': 'allow',
      'cms:manage': 'allow',
    },
  });

  await page.route('**/api/cms/v2/sites**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(SITES_FIXTURE),
    });
  });

  await page.route(`**/api/cms/v2/sites/${SITE_KEY}/pages**`, async (route) => {
    const method = route.request().method();
    if (method === 'POST') {
      const body = route.request().postDataJSON() as { title: string; slug: string };
      const createdPage = {
        id: 'page-created',
        site_id: 'site-1',
        slug: body.slug,
        title: body.title,
        status: 'draft',
        seo_json: {},
        published_version_id: null,
        publish_at: null,
        expires_at: null,
        created_at: '2026-07-16T10:00:00Z',
        updated_at: '2026-07-16T10:00:00Z',
      };
      pagesState = [createdPage, ...pagesState];
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(createdPage),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        items: pagesState,
        total: pagesState.length,
      }),
    });
  });

  await page.route(`**/api/cms/v2/sites/${SITE_KEY}/pages/*/workflow`, async (route) => {
    const body = route.request().postDataJSON() as { action: string };
    const slug = route.request().url().split('/pages/')[1]?.split('/workflow')[0] ?? '';
    const current = pagesState.find((item) => item.slug === slug);
    const nextStatus = body.action === 'archive' ? 'archived' : body.action === 'revert_draft' ? 'draft' : current?.status ?? 'draft';
    const updatedPage = {
      ...(current ?? pagesState[0]),
      slug,
      status: nextStatus,
    };
    pagesState = pagesState.map((item) => (item.slug === slug ? updatedPage : item));

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(updatedPage),
    });
  });

  await page.route(`**/api/cms/v2/sites/${SITE_KEY}/pages/*`, async (route) => {
    if (route.request().method() !== 'PATCH') {
      await route.continue();
      return;
    }
    const body = route.request().postDataJSON() as Record<string, unknown>;
    const slug = route.request().url().split('/pages/')[1] ?? 'bienvenida';
    const current = pagesState.find((item) => item.slug === slug) ?? pagesState[0];
    const updatedPage = {
      ...current,
      ...body,
      seo_json: {
        ...current.seo_json,
        ...(body.seo_json as Record<string, unknown> | undefined),
      },
    };
    pagesState = pagesState.map((item) => (item.slug === slug ? updatedPage : item));
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(updatedPage),
    });
  });

  await page.route(`**/api/cms/v2/sites/${SITE_KEY}/pages/bienvenida/preview`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(PREVIEW_FIXTURE),
    });
  });

  await page.route(`**/api/cms/v2/public/sites/${SITE_KEY}/theme`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(THEME_FIXTURE),
    });
  });
}

test.describe('CMS pages and preview deep smoke', () => {
  test.beforeEach(async ({ page }) => {
    await installCmsDeepMocks(page);
  });

  test('renders pages management, filters content and surfaces schedule views', async ({ page }) => {
    await page.goto('/plataforma/cms/pages', { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    await expect(page.locator('body')).toContainText(/Gestion de paginas/i);
    await expect(page.locator('body')).toContainText(/Página de Bienvenida/i);
    await expect(page.locator('body')).toContainText(/Retiro de Jóvenes/i);
    await expect(page.locator('body')).toContainText(/Campamento de Familias/i);

    await page.getByPlaceholder(/Buscar paginas/i).fill('retiro');
    await expect(page.locator('body')).toContainText(/Retiro de Jóvenes/i);
    await expect(page.locator('body')).not.toContainText(/Página de Bienvenida/i);

    await page.getByPlaceholder(/Buscar paginas/i).fill('');
    await page.getByRole('button', { name: /^Calendario$/i }).click();
    await expect(page.locator('body')).toContainText(/Calendario de paginas/i);
    await expect(page.locator('body')).toContainText(/Próximos 7 días/i);
    await expect(page.locator('body')).toContainText(/Publicación/i);

    await page.getByRole('button', { name: /^Gantt$/i }).click();
    await expect(page.locator('body')).toContainText(/CMS Pages/i);
    await expect(page.locator('body')).toContainText(/Página de Bienvenida/i);
  });

  test('creates a page and archives a selected draft from the management screen', async ({ page }) => {
    await page.goto('/plataforma/cms/pages', { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    await page.getByRole('button', { name: /Nueva pagina/i }).click();
    await page.getByPlaceholder(/Titulo de la nueva pagina/i).fill('Nueva Landing Faro');
    await page.getByRole('button', { name: /^Guardar$/i }).click();

    await expect(page.locator('body')).toContainText(/Nueva Landing Faro/i);

    await page.getByRole('button', { name: /^Tabla$/i }).click();
    const draftRow = page.getByRole('row').filter({ hasText: /Retiro de Jóvenes/i });
    await draftRow.getByRole('checkbox').check();
    await expect(page.locator('body')).toContainText(/1 seleccionadas/i);

    await page.getByRole('button', { name: /Archivar seleccion/i }).click();
    await expect(draftRow).toContainText(/Archivado/i);
  });

  test('renders preview draft with visible sections and refresh controls', async ({ page }) => {
    await page.goto(`/plataforma/cms/preview?site=${SITE_KEY}&page=bienvenida`, { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    await expect(page.locator('body')).toContainText(/Vista previa CMS/i);
    await expect(page.locator('body')).toContainText(/Página de Bienvenida/i);
    await expect(page.locator('body')).toContainText(/Draft actual/i);
    await expect(page.locator('body')).toContainText(/Bienvenidos a Faro/i);
    await expect(page.locator('body')).toContainText(/Banner/i);
    await expect(page.locator('body')).not.toContainText(/No debe verse/i);

    await page.getByRole('button', { name: /Auto/i }).click();
    await expect(page.locator('body')).toContainText(/Pausado/i);

    await page.getByRole('button', { name: /Recargar/i }).click();
    await expect(page.locator('body')).toContainText(/Bienvenidos a Faro/i);

    const publishedLink = page.getByRole('link', { name: /Publicado/i });
    await expect(publishedLink).toHaveAttribute('href', `/${SITE_KEY}/bienvenida`);
  });
});
