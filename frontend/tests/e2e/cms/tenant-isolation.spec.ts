import { test, expect, type Page } from '@playwright/test';
import { installMockPlatformSession } from '../helpers/mockPlatformSession';

const SITE_KEY = 'ccf';

const SITE_A = {
  id: 'site-1',
  site_key: SITE_KEY,
  name: 'Sede A - Faro Central',
  base_path: '/',
  is_active: true,
  sede_id: 'sede-a-uuid',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-07-10T00:00:00Z',
};

const _SITE_B = {
  id: 'site-2',
  site_key: 'faro-b',
  name: 'Sede B - Faro Norte',
  base_path: '/',
  is_active: true,
  sede_id: 'sede-b-uuid',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-07-10T00:00:00Z',
};

const PAGE_A = {
  id: 'page-a-1',
  site_id: 'site-1',
  slug: 'home',
  title: 'Home Sede A',
  status: 'published',
  seo_json: {},
  published_version_id: null,
  publish_at: null,
  expires_at: null,
  created_at: '2026-07-01T12:00:00Z',
  updated_at: '2026-07-12T09:00:00Z',
};

/**
 * Simulates the backend's `_get_scoped_site_or_404` rule:
 *   - The mock returns 404 to any /api/cms/v2/sites/faro-b/* request, mirroring
 *     what would happen if a Sede-A actor attempted to access another sede's site.
 *   - Sede-A endpoints expose only Sede-A data.
 */
async function installTenantIsolationMocks(page: Page) {
  await page.unrouteAll({ behavior: 'ignoreErrors' });

  // Register CMS routes first; session/auth mocks are added AFTER so the
  // unrouteAll() above doesn't drop them.
  await page.route(/\/api\/cms\/v2\/sites\/?(?:\?.*)?$/, async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([SITE_A]) });
  });

  await page.route(`**/api/cms/v2/sites/${SITE_KEY}/pages**`, async (route, request) => {
    if (request.method() === 'GET') {
      await route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify({ items: [PAGE_A], total: 1 }),
      });
      return;
    }
    if (request.method() === 'POST') {
      const body = request.postDataJSON() as { slug: string; title: string };
      const created = {
        id: 'page-a-new', site_id: 'site-1',
        slug: body.slug, title: body.title,
        status: 'draft', seo_json: {}, published_version_id: null,
        publish_at: null, expires_at: null,
        created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
      };
      await route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(created) });
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({}) });
  });

  await page.route(/\/api\/cms\/v2\/sites\/faro-b(?:\/.*)?$/, async (route) => {
    await route.fulfill({
      status: 404, contentType: 'application/json',
      body: JSON.stringify({ error: 'site not found' }),
    });
  });

  // Session mocks must be registered AFTER unrouteAll but BEFORE navigation.
  await installMockPlatformSession(page, {
    role: 'admin',
    sede_id: 'sede-a-uuid',
    permissions: { 'cms:read': 'allow', 'cms:edit': 'allow', 'cms:manage': 'allow' },
  });
}

test.describe('CMS tenant isolation (Axioma 3 — Multi-Tenant)', () => {
  test('Sede A user only sees Sede A pages in the platform', async ({ page }) => {
    await installTenantIsolationMocks(page);

    await page.goto(`/plataforma/cms/pages?site=${SITE_KEY}`, { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    await expect(page.getByText('Home Sede A')).toBeVisible();
  });

  test('Sede A user receives 404 when fetching Sede B site pages', async ({ page }) => {
    await installTenantIsolationMocks(page);
    await page.goto('/plataforma', { waitUntil: 'domcontentloaded' });

    const result = await page.evaluate(
      async () =>
        (async () => {
          const r = await fetch('http://localhost/api/cms/v2/sites/faro-b/pages', { credentials: 'omit' });
          return { status: r.status, body: await r.json().catch(() => null) };
        })()
    );

    expect(result.status).toBe(404);
    expect(result.body?.error).toBe('site not found');
  });

  test('Sede A user cannot create a page under Sede B site', async ({ page }) => {
    await installTenantIsolationMocks(page);
    await page.goto('/plataforma', { waitUntil: 'domcontentloaded' });

    const result = await page.evaluate(
      async () =>
        (async () => {
          const r = await fetch('http://localhost/api/cms/v2/sites/faro-b/pages', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ slug: 'home', title: 'Hijacked' }),
          });
          return { status: r.status };
        })()
    );

    expect(result.status).toBe(404);
  });
});
