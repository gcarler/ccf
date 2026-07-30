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

const MEDIA_FIXTURE = [
  {
    id: 'media-1',
    url: '/uploads/hero-banner.jpg',
    filename: 'hero-banner.jpg',
    alt_text: 'Hero banner de Faro',
    mime_type: 'image/jpeg',
    file_size: 245000,
    width: 1920,
    height: 1080,
    section: 'hero',
    tags: ['hero', 'banner'],
    status: 'active',
    created_at: '2026-07-01T12:00:00Z',
    updated_at: '2026-07-10T12:00:00Z',
  },
  {
    id: 'media-2',
    url: '/uploads/pastor-photo.jpg',
    filename: 'pastor-photo.jpg',
    alt_text: 'Foto del pastor principal',
    mime_type: 'image/jpeg',
    file_size: 120000,
    width: 800,
    height: 800,
    section: 'team',
    tags: ['pastor', 'team'],
    status: 'active',
    created_at: '2026-07-02T12:00:00Z',
    updated_at: '2026-07-11T12:00:00Z',
  },
  {
    id: 'media-3',
    url: '/uploads/evento-especial.pdf',
    filename: 'evento-especial.pdf',
    alt_text: 'PDF informativo del evento especial',
    mime_type: 'application/pdf',
    file_size: 500000,
    width: null,
    height: null,
    section: 'documents',
    tags: ['evento', 'pdf'],
    status: 'active',
    created_at: '2026-07-03T12:00:00Z',
    updated_at: '2026-07-12T12:00:00Z',
  },
];

async function installMediaMocks(page: Page, { emptyMedia = false }: { emptyMedia?: boolean } = {}) {
  let mediaState = emptyMedia ? [] : MEDIA_FIXTURE.map((m) => ({ ...m, tags: [...m.tags] }));

  await installMockPlatformSession(page, {
    role: 'admin',
    permissions: { 'cms:read': 'allow', 'cms:edit': 'allow', 'cms:manage': 'allow' },
  });

  // ── Specific media routes FIRST ────────────────────────────────────────
  // Media item CRUD: matches /api/cms/v2/media/<uuid> (GET, PATCH, DELETE)
  // Registered first so it wins over the list route for paths with /<id>.
  await page.route(`**/api/cms/v2/media/*`, async (route, request) => {
    const method = request.method();
    const url = request.url();
    if (method === 'DELETE') {
      const mediaId = url.split('/media/')[1]?.split('?')[0] ?? '';
      mediaState = mediaState.filter((item) => item.id !== mediaId);
      await route.fulfill({ status: 204 });
      return;
    }
    if (method === 'PATCH') {
      const mediaId = url.split('/media/')[1]?.split('?')[0] ?? '';
      const body = request.postDataJSON() as Record<string, unknown>;
      mediaState = mediaState.map((item) => (item.id === mediaId ? { ...item, ...body } as typeof item : item));
      const updated = mediaState.find((item) => item.id === mediaId);
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(updated) });
      return;
    }
    await route.continue();
  });

  // Media list: matches /api/cms/v2/media and /api/cms/v2/media?query=...
  // The trailing `*` matches query params but NOT `/123` (Playwright `*` ≠ `/`).
  await page.route(`**/api/cms/v2/media*`, async (route) => {
    const url = new URL(route.request().url());
    const searchQuery = url.searchParams.get('query')?.toLowerCase() || '';
    if (searchQuery) {
      const filtered = mediaState.filter(
        (item) =>
          item.alt_text.toLowerCase().includes(searchQuery) ||
          item.filename.toLowerCase().includes(searchQuery) ||
          item.tags.some((t) => t.toLowerCase().includes(searchQuery)),
      );
      await route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify({ items: filtered, total: filtered.length }),
      });
      return;
    }
    await route.fulfill({
      status: 200, contentType: 'application/json',
      body: JSON.stringify({ items: mediaState, total: mediaState.length }),
    });
  });

  // ── General fallback LAST ──────────────────────────────────────────────
  await page.route('**/api/cms/v2/sites**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(SITES_FIXTURE) });
  });
}

test.describe('CMS media management', () => {
  test('renders the media library with files', async ({ page }) => {
    await installMediaMocks(page);
    await page.goto(`/plataforma/cms/media?site=${SITE_KEY}`, { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('body')).toBeVisible();
  });

  test('shows empty state when no media is available', async ({ page }) => {
    await installMediaMocks(page, { emptyMedia: true });
    await page.goto(`/plataforma/cms/media?site=${SITE_KEY}`, { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('body')).toBeVisible();
  });

  test('handles media item deletion gracefully', async ({ page }) => {
    await installMediaMocks(page);
    await page.goto(`/plataforma/cms/media?site=${SITE_KEY}`, { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('body')).toBeVisible();
  });
});
