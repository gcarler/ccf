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
  // Clear any previously registered mocks to avoid stale handlers across tests
  await page.unrouteAll({ behavior: 'ignoreErrors' });

  let mediaState = emptyMedia ? [] : MEDIA_FIXTURE.map((m) => ({ ...m, tags: [...m.tags] }));

  await installMockPlatformSession(page, {
    role: 'admin',
    permissions: { 'cms:read': 'allow', 'cms:edit': 'allow', 'cms:manage': 'allow' },
  });

  // ── Specific media routes FIRST ────────────────────────────────────────
  // The media page uses apiFetch("/cms/media", ...), which resolves to
  // apiUrl("/cms/media") => /api/cms/media (no "v2" prefix).
  // Playwright dispatches handlers in registration order; most specific routes
  // must be registered BEFORE more general ones to win.

  // Media upload endpoint: most specific sub-path, registered first
  await page.route(`**/api/cms/media/upload`, async (route) => {
    await route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
  });

  // Media item CRUD: matches /api/cms/media/<id> (GET, PATCH, POST, DELETE)
  await page.route(`**/api/cms/media/*`, async (route, request) => {
    const method = request.method();
    const url = request.url();
    const mediaId = url.split('/media/')[1]?.split('?')[0] ?? '';

    // POST to /media/<id>/optimize — handle it here so it doesn't fall through
    if (method === 'POST' && url.includes('/optimize')) {
      const updatedItem = mediaState.find((item) => item.id === mediaId);
      if (updatedItem) {
        mediaState = mediaState.map((item) =>
          item.id === mediaId
            ? { ...item, file_size: Math.round((item.file_size || 0) * 0.7) } as typeof item
            : item
        );
      }
      await route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify({ ...updatedItem, optimized: true }),
      });
      return;
    }

    if (method === 'DELETE') {
      if (url.includes('permanent=true')) {
        mediaState = mediaState.filter((item) => item.id !== mediaId);
      } else {
        mediaState = mediaState.map((item) =>
          item.id === mediaId ? { ...item, status: 'archived' } : item
        );
      }
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
      return;
    }

    if (method === 'PATCH') {
      const body = request.postDataJSON() as Record<string, unknown>;
      mediaState = mediaState.map((item) =>
        item.id === mediaId ? { ...item, ...body } as typeof item : item
      );
      const updated = mediaState.find((item) => item.id === mediaId);
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(updated) });
      return;
    }

    await route.continue();
  });

  // Media list: matches /api/cms/media and /api/cms/media?query=...
  await page.route(`**/api/cms/media*`, async (route) => {
    const url = new URL(route.request().url());
    // If URL has a path segment after /media/ (like /media/123), skip — handled above
    if (url.pathname.replace(/\/$/, '').split('/media/')[1]?.length) {
      await route.fallback();
      return;
    }
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

    // Verify header
    await expect(page.getByText('Biblioteca de Medios')).toBeVisible();

    // Verify file count badge shows correct number
    await expect(page.getByText('3 archivos')).toBeVisible();

    // Verify all three media filenames are visible
    await expect(page.getByText('hero-banner.jpg', { exact: false })).toBeVisible();
    await expect(page.getByText('pastor-photo.jpg', { exact: false })).toBeVisible();
    await expect(page.getByText('evento-especial.pdf', { exact: false })).toBeVisible();

    // Verify upload button is present
    await expect(page.getByText('Subir Archivos')).toBeVisible();

    // Verify filter buttons are present
    await expect(page.getByText('Imágenes')).toBeVisible();
    await expect(page.getByText('Documentos')).toBeVisible();
  });

  test('shows empty state when no media is available', async ({ page }) => {
    await installMediaMocks(page, { emptyMedia: true });
    await page.goto(`/plataforma/cms/media?site=${SITE_KEY}`, { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    // Verify empty state message
    await expect(page.getByText('Biblioteca vacía')).toBeVisible();

    // Verify the "Subir primer archivo" button is shown on empty state
    await expect(page.getByText('Subir primer archivo')).toBeVisible();

    // Verify count shows zero
    await expect(page.getByText('0 archivos')).toBeVisible();
  });

  test('handles media item deletion and confirms removal from list', async ({ page }) => {
    await installMediaMocks(page);
    await page.goto(`/plataforma/cms/media?site=${SITE_KEY}`, { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    // Verify initial file count
    await expect(page.getByText('3 archivos')).toBeVisible();

    // Hover over the first media item to reveal action buttons
    // The delete button has aria-label="Eliminar"
    const firstItem = page.locator('text=hero-banner.jpg').first();
    await firstItem.hover();

    // Click the "Eliminar" button
    const deleteButton = page.locator('[aria-label="Eliminar"]').first();
    await expect(deleteButton).toBeVisible();
    await deleteButton.click();

    // Confirmation dialog should appear
    await expect(page.getByText('¿Eliminar permanentemente?')).toBeVisible();
    await expect(page.getByText('Esta acción no se puede deshacer.')).toBeVisible();

    // Cancel the action — item should still be in the list
    await page.getByRole('button', { name: 'Cancelar' }).click();
    await expect(page.getByText('hero-banner.jpg', { exact: false })).toBeVisible();
    await expect(page.getByText('3 archivos')).toBeVisible();

    // Re-open the delete dialog and confirm
    await firstItem.hover();
    await deleteButton.click();
    await expect(page.getByText('¿Eliminar permanentemente?')).toBeVisible();

    // Confirm deletion
    await page.getByRole('button', { name: 'Eliminar' }).click();

    // The item should disappear from the list and count should decrease
    await expect(page.getByText('hero-banner.jpg', { exact: false })).not.toBeVisible({ timeout: 5000 });
    await expect(page.getByText('2 archivos')).toBeVisible();
  });

  test('filters media by search query', async ({ page }) => {
    await installMediaMocks(page);
    await page.goto(`/plataforma/cms/media?site=${SITE_KEY}`, { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    // All 3 files visible initially
    await expect(page.getByText('3 archivos')).toBeVisible();

    // Type in search box to filter by filename
    const searchInput = page.getByPlaceholder('Buscar archivos');
    await expect(searchInput).toBeVisible();
    await searchInput.fill('pastor');
    await page.waitForTimeout(300); // Debounce on search

    // Only pastor-photo should remain
    await expect(page.getByText('pastor-photo.jpg', { exact: false })).toBeVisible();
    await expect(page.getByText('hero-banner.jpg', { exact: false })).not.toBeVisible();
    await expect(page.getByText('evento-especial.pdf', { exact: false })).not.toBeVisible();
    await expect(page.getByText('1 archivos')).toBeVisible();

    // Clear search — all should return
    await searchInput.fill('');
    await page.waitForTimeout(300);
    await expect(page.getByText('3 archivos')).toBeVisible();
  });

  test('filters media by type tab (Imágenes)', async ({ page }) => {
    await installMediaMocks(page);
    await page.goto(`/plataforma/cms/media?site=${SITE_KEY}`, { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    // Click the "Imágenes" filter tab
    await page.getByText('Imágenes').click();
    await page.waitForTimeout(300);

    // Only image files should remain (hero-banner.jpg, pastor-photo.jpg)
    await expect(page.getByText('hero-banner.jpg', { exact: false })).toBeVisible();
    await expect(page.getByText('pastor-photo.jpg', { exact: false })).toBeVisible();
    await expect(page.getByText('evento-especial.pdf', { exact: false })).not.toBeVisible();

    // Click "Documentos" filter
    await page.getByText('Documentos').click();
    await page.waitForTimeout(300);

    // Only PDF should remain
    await expect(page.getByText('hero-banner.jpg', { exact: false })).not.toBeVisible();
    await expect(page.getByText('evento-especial.pdf', { exact: false })).toBeVisible();

    // Click "Todos" to reset
    await page.getByText('Todos').click();
    await page.waitForTimeout(300);
    await expect(page.getByText('3 archivos')).toBeVisible();
  });
});
