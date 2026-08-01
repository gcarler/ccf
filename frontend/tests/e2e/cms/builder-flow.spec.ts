import { expect, test, type Page } from '@playwright/test';
import { installMockPlatformSession } from '../helpers/mockPlatformSession';

const SITE_KEY = 'ccf';

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

const PAGES_FIXTURE: Array<{
  id: string; site_id: string; slug: string; title: string; status: string;
  seo_json: Record<string, unknown>;
  published_version_id: string | null; publish_at: string | null; expires_at: string | null;
  created_at: string; updated_at: string;
}> = [
  {
    id: 'page-1', site_id: 'site-1', slug: 'landing',
    title: 'Landing Page', status: 'draft',
    seo_json: {}, published_version_id: null, publish_at: null, expires_at: null,
    created_at: '2026-07-01T12:00:00Z', updated_at: '2026-07-12T09:00:00Z',
  },
  {
    id: 'page-2', site_id: 'site-1', slug: 'nosotros',
    title: 'Acerca de Nosotros', status: 'published',
    seo_json: {}, published_version_id: null, publish_at: null, expires_at: null,
    created_at: '2026-07-01T12:00:00Z', updated_at: '2026-07-12T09:00:00Z',
  },
];

const SECTIONS_FIXTURE = [
  {
    id: 'section-1',
    page_id: 'page-1',
    section_key: 'hero-1',
    type: 'hero',
    props_json: { title: 'Hero Title', subtitle: 'Hero subtitle', cta_text: 'Learn More', cta_link: '/about' },
    sort_order: 1,
    is_visible: true,
    status: 'active',
    created_at: '2026-07-01T12:00:00Z',
    updated_at: '2026-07-10T12:00:00Z',
  },
  {
    id: 'section-2',
    page_id: 'page-1',
    section_key: 'cta-1',
    type: 'cta_banner',
    props_json: { title: 'Join Us', description: 'Everyone is welcome.', button_text: 'Visit', button_link: '/contact' },
    sort_order: 2,
    is_visible: true,
    status: 'active',
    created_at: '2026-07-01T12:00:00Z',
    updated_at: '2026-07-10T12:00:00Z',
  },
];

const PREVIEW_FIXTURE = {
  site_key: SITE_KEY,
  slug: 'landing',
  title: 'Landing Page',
  seo_json: {},
  canonical_url: 'https://faro.ccf.local/landing',
  sections: SECTIONS_FIXTURE,
};

const SECTION_TYPES_FIXTURE = [
  { name: 'hero', is_active: true },
  { name: 'cta_banner', is_active: true },
  { name: 'rich_text', is_active: true },
  { name: 'faq', is_active: true },
  { name: 'stats', is_active: true },
  { name: 'team', is_active: true },
  { name: 'testimonials', is_active: true },
  { name: 'gallery', is_active: true },
  { name: 'pricing', is_active: true },
];

const THEME_FIXTURE = {
  id: 'theme-1',
  site_id: 'site-1',
  name: 'Tema Faro',
  tokens_json: { '--site-background': '#f6f7fb', '--site-primary': '#0f4c81' },
  is_active: true,
  status: 'active',
  version: 3,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-07-01T00:00:00Z',
};

async function installBuilderMocks(page: Page) {
  // Clear any previously registered mocks to avoid stale handlers across tests
  await page.unrouteAll({ behavior: 'ignoreErrors' });

  let pagesState = PAGES_FIXTURE.map((p) => ({ ...p, seo_json: { ...p.seo_json } }));
  let sectionsState = SECTIONS_FIXTURE.map((s) => ({ ...s, props_json: { ...s.props_json } }));
  let sectionCounter = 3;

  await installMockPlatformSession(page, {
    role: 'admin',
    permissions: { 'cms:read': 'allow', 'cms:edit': 'allow', 'cms:manage': 'allow' },
  });

  // ── Specific routes FIRST ──────────────────────────────────────────────
  // Playwright dispatches handlers in registration order; specific routes
  // must be registered BEFORE the general fallback to win.

  await page.route('**/api/cms/v2/section-types**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(SECTION_TYPES_FIXTURE) });
  });

  await page.route(`**/api/cms/v2/sites/${SITE_KEY}/pages/landing/preview`, async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(PREVIEW_FIXTURE) });
  });

  await page.route(`**/api/cms/v2/sites/${SITE_KEY}/pages/landing/sections**`, async (route) => {
    const method = route.request().method();
    if (method === 'POST') {
      const body = route.request().postDataJSON() as any;
      sectionCounter += 1;
      const created = {
        id: `section-${sectionCounter}`, page_id: 'page-1', section_key: `new-${sectionCounter}`,
        type: body.type, props_json: body.props_json || {}, sort_order: sectionsState.length + 1,
        is_visible: true, status: 'active',
        created_at: '2026-07-16T10:00:00Z', updated_at: '2026-07-16T10:00:00Z',
      };
      sectionsState = [...sectionsState, created];
      await route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(created) });
      return;
    }
    await route.fulfill({
      status: 200, contentType: 'application/json',
      body: JSON.stringify({ items: sectionsState, total: sectionsState.length }),
    });
  });

  await page.route(`**/api/cms/v2/sites/${SITE_KEY}/pages/*/workflow`, async (route) => {
    const body = route.request().postDataJSON() as { action: string };
    const slug = route.request().url().split('/pages/')[1]?.split('/workflow')[0] ?? '';
    const current = pagesState.find((item) => item.slug === slug);
    const nextStatus = body.action === 'publish' ? 'published' : body.action === 'archive' ? 'archived' : 'draft';
    const updatedPage = { ...(current ?? pagesState[0]), slug, status: nextStatus };
    pagesState = pagesState.map((item) => (item.slug === slug ? updatedPage : item));
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(updatedPage) });
  });

  // Pages list/create: uses `fallback()` for sub-routes so specific handlers win.
  await page.route(new RegExp(`/api/cms/v2/sites/${SITE_KEY}/pages/?(?:\\?.*)?$`), async (route) => {
    const method = route.request().method();
    if (method === 'POST') {
      const body = route.request().postDataJSON() as { title: string; slug: string };
      const createdPage = {
        id: 'page-created', site_id: 'site-1', slug: body.slug, title: body.title,
        status: 'draft', seo_json: {}, published_version_id: null,
        publish_at: null, expires_at: null,
        created_at: '2026-07-16T10:00:00Z', updated_at: '2026-07-16T10:00:00Z',
      };
      pagesState = [createdPage, ...pagesState];
      await route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(createdPage) });
      return;
    }
    await route.fulfill({
      status: 200, contentType: 'application/json',
      body: JSON.stringify({ items: pagesState, total: pagesState.length }),
    });
  });

  await page.route(`**/api/cms/v2/public/sites/${SITE_KEY}/theme`, async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(THEME_FIXTURE) });
  });

  // ── General fallback LAST ──────────────────────────────────────────────
  // Only matches when no more specific route has already fulfilled.
  await page.route(/\/api\/cms\/v2\/sites\/?(?:\?.*)?$/, async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(SITES_FIXTURE) });
  });
}

test.describe('CMS builder flow', () => {
  test.beforeEach(async ({ page }) => {
    await installBuilderMocks(page);
  });

  test('renders pages list with site pages', async ({ page }) => {
    await page.goto(`/plataforma/cms/pages?site=${SITE_KEY}`, { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    // Verify header
    await expect(page.getByText('Gestion de paginas')).toBeVisible();

    // Verify page from fixture renders with title, slug, and status
    await expect(page.getByText('Landing Page')).toBeVisible();
    await expect(page.getByText('/landing')).toBeVisible();
    await expect(page.getByText('Borrador')).toBeVisible();

    // Verify action buttons are present
    await expect(page.getByText('Nueva pagina').first()).toBeVisible();
  });

  test('renders preview page with hero section data', async ({ page }) => {
    await page.goto(`/plataforma/cms/preview?site=${SITE_KEY}&page=landing`, { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    // Verify preview header shows page metadata
    await expect(page.getByText('Vista previa CMS')).toBeVisible();
    await expect(page.getByText('Landing Page')).toBeVisible();

    // Verify section content from fixtures renders
    await expect(page.getByText('Hero Title')).toBeVisible();
    await expect(page.getByText('Join Us')).toBeVisible();
    await expect(page.locator('main').filter({ hasText: 'Hero Title' }).last()).toContainText('Join Us');

    // Verify auto-refresh and reload controls
    await expect(page.getByText('Recargar')).toBeVisible();
  });

  test('creates a new page via quick add', async ({ page }) => {
    await page.goto(`/plataforma/cms/pages?site=${SITE_KEY}`, { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    // Click "Nueva pagina" to open quick-add form
    await page.getByText('Nueva pagina').first().click();

    // Type a title in the quick-add input
    const quickAddInput = page.getByPlaceholder('Titulo de la nueva pagina');
    await expect(quickAddInput).toBeVisible();
    await quickAddInput.fill('Acerca de');

    // Submit the form
    await page.getByRole('button', { name: 'Guardar' }).click();

    // The newly created page should appear in the list
    await expect(page.getByText('Acerca de')).toBeVisible();
    // The slug should be auto-generated: "acerca-de"
    await expect(page.getByText('/acerca-de')).toBeVisible();
  });

  test('archives a page and confirms dialog', async ({ page }) => {
    await page.goto(`/plataforma/cms/pages?site=${SITE_KEY}`, { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    // Click the archive button on the first page card
    const archiveButton = page.locator('button[title="Archivar pagina"]').first();
    await expect(archiveButton).toBeVisible();
    await archiveButton.click();

    // Confirmation dialog should appear
    await expect(page.getByText('¿Archivar página?')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Landing Page', exact: true })).toBeVisible();

    // Cancel the action — page should still be visible
    await page.getByRole('button', { name: 'Cancelar' }).click();
    await expect(page.getByRole('heading', { name: 'Landing Page', exact: true })).toBeVisible();

    // Re-open dialog and confirm archive
    await archiveButton.click();
    await expect(page.getByText('¿Archivar página?')).toBeVisible();
    await page.getByRole('button', { name: 'Archivar', exact: true }).click();

    // Page status should update to archived — wait for the badge to appear
    await expect(page.getByText('Archivado').first()).toBeVisible({ timeout: 5000 });
  });

  test('switches between grid and table view', async ({ page }) => {
    await page.goto(`/plataforma/cms/pages?site=${SITE_KEY}`, { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    // Default view should be grid — verify page card is rendered
    await expect(page.getByText('Landing Page').first()).toBeVisible();

    // Find ViewSwitcher button for Table view (uses title attribute from ViewSwitcher)
    const tableButton = page.locator('button[title="Tabla"]');
    await expect(tableButton).toBeVisible();
    await tableButton.click();
    await page.waitForTimeout(300);

    // Table view renders column headers in the <thead>
    await expect(page.getByRole('columnheader', { name: 'Pagina', exact: true })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: 'Slug', exact: true })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: 'Estado', exact: true })).toBeVisible();

    // Switch back to grid view
    const gridButton = page.locator('button[title="Grid"]');
    await expect(gridButton).toBeVisible();
    await gridButton.click();
    await page.waitForTimeout(300);
    await expect(page.getByText('Landing Page').first()).toBeVisible();
  });

  test('filters pages with search input', async ({ page }) => {
    await page.goto(`/plataforma/cms/pages?site=${SITE_KEY}`, { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    // Both pages from fixture should be visible initially
    await expect(page.getByText('Landing Page').first()).toBeVisible();
    await expect(page.getByText('Acerca de Nosotros')).toBeVisible();

    // Type in search box to filter
    const searchInput = page.getByPlaceholder('Buscar paginas');
    await expect(searchInput).toBeVisible();
    await searchInput.fill('Landing');
    await page.waitForTimeout(300); // Debounce on search

    // Only Landing Page should remain
    await expect(page.getByText('Acerca de Nosotros')).not.toBeVisible();

    // Clear search — both should be visible again
    await searchInput.fill('');
    await page.waitForTimeout(300);
    await expect(page.getByText('Acerca de Nosotros')).toBeVisible();
  });
});
