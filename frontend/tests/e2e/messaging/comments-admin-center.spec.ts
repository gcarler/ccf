import { expect, test, type Page } from '@playwright/test';
import { installMockPlatformSession } from '../helpers/mockPlatformSession';
import type { ProjectCommentItem } from '@/types/projects';

const CURRENT_PERSONA_ID = 'e2e-persona';

const MENTIONS: ProjectCommentItem[] = [
  {
    id: 'c-4',
    project_id: 'p-1',
    content: '@pastor.e2e por favor revisa esto.',
    author_id: 'u-1',
    author_name: 'Ana Pérez',
    is_resolved: false,
    created_at: '2026-07-16T09:15:00Z',
    updated_at: '2026-07-16T09:15:00Z',
    module_type: 'project',
    context_title: 'Retiro de jóvenes',
    mentions: [CURRENT_PERSONA_ID],
  },
];

function generateMockItems(count: number, startId = 0): ProjectCommentItem[] {
  return Array.from({ length: count }, (_, i) => {
    const id = startId + i;
    return {
      id: `c-${id}`,
      project_id: `p-${id}`,
      content: `Comentario de prueba ${id}`,
      author_id: CURRENT_PERSONA_ID,
      author_name: 'Usuario E2E',
      is_resolved: false,
      created_at: new Date(Date.now() - id * 60_000).toISOString(),
      updated_at: new Date(Date.now() - id * 60_000).toISOString(),
      module_type: 'project',
      context_title: `Proyecto ${id}`,
    };
  });
}

const PAGE_1 = generateMockItems(50, 0);
const PAGE_2 = generateMockItems(5, 50);

async function installCommentsAdminMocks(page: Page) {
  await page.route('**/api/comments/me/created*', async (route) => {
    const url = new URL(route.request().url());
    const offset = Number(url.searchParams.get('offset') ?? '0');
    await new Promise((resolve) => setTimeout(resolve, 100));

    if (offset >= 50) {
      await route.fulfill({ status: 200, json: PAGE_2 });
    } else {
      await route.fulfill({ status: 200, json: PAGE_1 });
    }
  });

  await page.route('**/api/comments/me/mentions*', async (route) => {
    await route.fulfill({ status: 200, json: MENTIONS });
  });

  // Avoid unrelated 401 console noise from the layout
  await page.route('**/api/workspace/config', async (route) => {
    await route.fulfill({ status: 200, json: {} });
  });
}

test.describe('Comments admin center', () => {
  test.beforeEach(async ({ page }) => {
    await installMockPlatformSession(page, {
      role: 'admin',
      permissions: {
        'messaging:read': 'allow',
        'messaging:edit': 'allow',
      },
    });

    await installCommentsAdminMocks(page);
    await page.emulateMedia({ reducedMotion: 'reduce' });
  });

  test('renders authored comments and supports tab switching', async ({ page }) => {
    await page.goto('/plataforma/inbox/comments', { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    await expect(page.locator('body')).toContainText('Centro de comentarios');
    await expect(page.locator('body')).toContainText('Mis comentarios');
    await expect(page.locator('body')).toContainText('Menciones');

    // Default tab shows authored comments (mocked as PAGE_1)
    await expect(page.locator('body')).toContainText('Comentario de prueba 0');
    await expect(page.locator('body')).toContainText('Proyecto 0');
    await expect(page.locator('body')).toContainText('Comentario de prueba 49');

    await page.getByRole('tab', { name: /Menciones/i }).click();
    await expect(page.locator('body')).toContainText('@pastor.e2e por favor revisa esto.');
    await expect(page.locator('body')).toContainText('Ana Pérez');
  });

  test('filters results by search term', async ({ page }) => {
    await page.goto('/plataforma/inbox/comments', { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    await page.getByLabel(/Buscar comentarios/i).fill('Comentario de prueba 5');
    await expect(page.locator('body')).toContainText('Comentario de prueba 5');
    await expect(page.locator('body')).not.toContainText('Comentario de prueba 0');
  });

  test('filters by module type', async ({ page }) => {
    await page.goto('/plataforma/inbox/comments', { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    await page.getByLabel(/Filtrar por módulo/i).selectOption('project');
    await expect(page.locator('body')).toContainText('Proyecto 0');
  });

  test('navigates to the project when an item is clicked', async ({ page }) => {
    await page.goto('/plataforma/inbox/comments', { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    const link = page.locator('a[href="/plataforma/proyectos/p-0"]').first();
    await expect(link).toBeVisible();
    await link.click();

    await expect(page).toHaveURL(/\/plataforma\/proyectos\/p-0/);
  });

  test('loads comments, shows loading state, and supports pagination', async ({ page }) => {
    const consoleErrors: string[] = [];
    const apiErrors: { status: number; url: string }[] = [];

    page.on('console', (msg) => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });

    page.on('response', (response) => {
      if (response.status() >= 400 && response.url().includes('/api/')) {
        apiErrors.push({ status: response.status(), url: response.url() });
      }
    });

    await page.goto('/plataforma/inbox/comments', { waitUntil: 'load' });

    await expect(page.getByText('Cargando comentarios…')).toBeVisible();
    await expect(page.getByText('Cargando comentarios…')).toBeHidden();

    await expect(page.getByText('50 resultados')).toBeVisible();
    await expect(page.getByText('Comentario de prueba 0')).toBeVisible();

    const loadMoreBtn = page.getByRole('button', { name: 'Cargar más comentarios' });
    await expect(loadMoreBtn).toBeVisible();

    await loadMoreBtn.click();
    await expect(page.getByText('Cargando más…')).toBeVisible();
    await expect(page.getByText('Cargando más…')).toBeHidden();

    await expect(page.getByText('55 resultados')).toBeVisible();
    await expect(page.getByText('Comentario de prueba 50')).toBeVisible();
    await expect(loadMoreBtn).toBeHidden();

    expect(consoleErrors, 'No console errors expected').toEqual([]);
    expect(apiErrors, 'No API errors expected').toEqual([]);
  });
});
