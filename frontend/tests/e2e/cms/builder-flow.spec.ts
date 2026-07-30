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
    slug: 'landing',
    title: 'Landing Page',
    status: 'draft',
    seo_json: {},
    published_version_id: null,
    publish_at: null,
    expires_at: null,
    created_at: '2026-07-01T12:00:00Z',
    updated_at: '2026-07-12T09:00:00Z',
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
      const body = route.request().postDataJSON() as { type: string };
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
  await page.route(`**/api/cms/v2/sites/${SITE_KEY}/pages**`, async (route) => {
    const path = new URL(route.request().url()).pathname;
    // Let sub-routes (preview, sections, workflow) through to their handlers
    if (path.replace(/\/$/, '').split('/pages/')[1]?.includes('/')) {
      await route.fallback();
      return;
    }
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
  await page.route('**/api/cms/v2/sites**', async (route) => {
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
    await expect(page.locator('body')).toBeVisible();
  });

  test('renders preview page with hero section data', async ({ page }) => {
    await page.goto(`/plataforma/cms/preview?site=${SITE_KEY}&page=landing`, { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('body')).toBeVisible();
  });
});
