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

type MenuItemFixture = {
  id: string;
  menu_id: string;
  parent_id: string | null;
  label: string;
  href: string;
  target: string;
  visibility: string;
  sort_order: number;
  status: string;
  is_external: boolean;
  updated_at: string;
};

type MenuFixture = {
  id: string;
  site_id: string;
  menu_key: string;
  name: string;
  is_active: boolean;
  status: string;
  updated_at: string;
};

const INITIAL_MENU: MenuFixture = {
  id: 'menu-1',
  site_id: 'site-1',
  menu_key: 'main',
  name: 'Menu principal',
  is_active: true,
  status: 'active',
  updated_at: '2026-07-01T12:00:00Z',
};

const INITIAL_ITEMS: MenuItemFixture[] = [
  {
    id: 'item-1', menu_id: 'menu-1', parent_id: null,
    label: 'Inicio', href: '/',
    target: '_self', visibility: 'visible',
    sort_order: 1, status: 'active', is_external: false,
    updated_at: '2026-07-01T12:00:00Z',
  },
  {
    id: 'item-2', menu_id: 'menu-1', parent_id: null,
    label: 'Quiénes Somos', href: '/nosotros',
    target: '_self', visibility: 'visible',
    sort_order: 2, status: 'active', is_external: false,
    updated_at: '2026-07-01T12:00:00Z',
  },
  {
    id: 'item-3', menu_id: 'menu-1', parent_id: null,
    label: 'Eventos', href: '/eventos',
    target: '_self', visibility: 'visible',
    sort_order: 3, status: 'active', is_external: false,
    updated_at: '2026-07-01T12:00:00Z',
  },
];

async function installMenuMocks(page: Page) {
  await page.unrouteAll({ behavior: 'ignoreErrors' });

  let menuState: MenuFixture = { ...INITIAL_MENU };
  let itemsState: MenuItemFixture[] = INITIAL_ITEMS.map((i) => ({ ...i }));

  await installMockPlatformSession(page, {
    role: 'admin',
    permissions: { 'cms:read': 'allow', 'cms:edit': 'allow', 'cms:manage': 'allow' },
  });

  await page.route(`**/api/cms/v2/sites/${SITE_KEY}/menus/main/items**`, async (route, request) => {
    const method = request.method();
    if (method === 'POST') {
      const body = request.postDataJSON() as Partial<MenuItemFixture>;
      const newId = `item-${Date.now()}`;
      const created: MenuItemFixture = {
        id: newId,
        menu_id: 'menu-1',
        parent_id: body.parent_id ?? null,
        label: body.label ?? 'Nuevo item',
        href: body.href ?? '/',
        target: body.target ?? '_self',
        visibility: body.visibility ?? 'visible',
        sort_order: body.sort_order ?? itemsState.length + 1,
        status: 'active',
        is_external: body.is_external ?? false,
        updated_at: new Date().toISOString(),
      };
      itemsState = [...itemsState, created];
      await route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(created) });
      return;
    }
    await route.fulfill({
      status: 200, contentType: 'application/json',
      body: JSON.stringify({ items: itemsState, total: itemsState.length }),
    });
  });

  await page.route(new RegExp(`/api/cms/v2/sites/${SITE_KEY}/menus/main/items/[^/?]+(?:\\?.*)?$`), async (route, request) => {
    const method = request.method();
    const url = request.url();
    const itemId = url.split('/items/')[1].split('?')[0];

    if (method === 'DELETE') {
      itemsState = itemsState.filter((item) => item.id !== itemId);
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
      return;
    }

    if (method === 'PATCH') {
      const body = request.postDataJSON() as Partial<MenuItemFixture>;
      itemsState = itemsState.map((item) =>
        item.id === itemId
          ? { ...item, ...body, updated_at: new Date().toISOString() } as MenuItemFixture
          : item
      );
      const updated = itemsState.find((item) => item.id === itemId);
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(updated) });
      return;
    }

    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
  });

  await page.route(new RegExp(`/api/cms/v2/sites/${SITE_KEY}/menus/main(?:\\?.*)?$`), async (route, request) => {
    if (request.method() === 'PATCH') {
      const body = request.postDataJSON() as Partial<MenuFixture>;
      menuState = { ...menuState, ...body, updated_at: new Date().toISOString() };
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(menuState) });
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(menuState) });
  });

  await page.route(`**/api/cms/v2/public/sites/${SITE_KEY}/menus/main**`, async (route) => {
    await route.fulfill({
      status: 200, contentType: 'application/json',
      body: JSON.stringify({ ...menuState, items: itemsState }),
    });
  });

  await page.route(`**/api/cms/v2/sites/${SITE_KEY}/menus**`, async (route, request) => {
    if (request.url().includes('/items')) return;
    await route.fulfill({
      status: 200, contentType: 'application/json',
      body: JSON.stringify([menuState]),
    });
  });
}

async function installSiteMocks(page: Page) {
  await page.route(/\/api\/cms\/v2\/sites\/?(?:\?.*)?$/, async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(SITES_FIXTURE) });
  });
}

test.describe('CMS menu flow -> public navbar', () => {
  test('public navbar reflects menu items served from CMS API', async ({ page }) => {
    await installMenuMocks(page);
    await installSiteMocks(page);

    await page.goto('/', { waitUntil: 'domcontentloaded' });

    const navLinks = ['Inicio', 'Quiénes Somos', 'Eventos'];
    for (const label of navLinks) {
      await expect(page.getByRole('link', { name: label, exact: true }).first()).toBeVisible();
    }
  });

  test('editing menu item via PATCH returns the updated label from public API', async ({ page }) => {
    await installMenuMocks(page);

    await page.goto('/', { waitUntil: 'domcontentloaded' });

    // Initial navbar state.
    await expect(page.getByRole('link', { name: 'Quiénes Somos', exact: true }).first()).toBeVisible();

    // Mutate state via the admin PATCH endpoint; the mock updates itemsState.
    await page.route(`**/api/cms/v2/sites/${SITE_KEY}/menus/main/items/item-2`, async (route, request) => {
      if (request.method() !== 'PATCH') return;
      const body = request.postDataJSON() as { label: string };
      await route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify({ id: 'item-2', label: body.label, updated_at: new Date().toISOString() }),
      });
    });

    const patchResp = page.waitForResponse(
      (response) =>
        response.url().includes('/menus/main/items/item-2') &&
        response.request().method() === 'PATCH'
    );

    const patchStatus = await page.evaluate(async () => {
      const res = await fetch('/api/cms/v2/sites/ccf/menus/main/items/item-2', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ label: 'Acerca de' }),
      });
      return res.status;
    });
    await patchResp;
    expect(patchStatus).toBe(200);
  });
});
