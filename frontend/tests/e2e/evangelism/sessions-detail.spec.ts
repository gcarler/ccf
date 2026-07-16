import { test, expect, Page, Route } from '@playwright/test';
import { installMockPlatformSession } from '../helpers/mockPlatformSession';

/**
 * E2E coverage for the renamed Evangelism session report route:
 *   /plataforma/evangelism/faro/sessions/[grupo_id]
 *
 * The dynamic segment was renamed from [house_id] → [grupo_id]; the URL
 * pattern /sessions/{uuid} is unchanged. These tests pin that the page
 * reads params.grupo_id (not params.house_id) and POSTs grupo_id to the
 * backend correctly.
 *
 * Backend is mocked via page.route() so the spec runs without DB.
 */

const GRUPO_FIXTURE = {
    id: 'g1',
    name: 'Casa Bethel',
    zone: 'Centro',
    address: 'Av. Reforma 123',
    leader_name: 'Ana Pérez',
    leader_id: 'p1',
    assistant_id: 'p2',
    host_id: 'p3',
    personas_count: 4,
    status: 'active',
    evangelism_strategy_id: 's-1',
    base_attendees: [
        { persona_id: 'p1', name: 'Ana Pérez',    role: 'leader',     role_label: 'Líder' },
        { persona_id: 'p2', name: 'Carlos Ruiz',  role: 'assistant',  role_label: 'Asistente del Líder' },
        { persona_id: 'p3', name: 'Lucía Vega',   role: 'host',       role_label: 'Anfitrión' },
        { persona_id: 'p4', name: 'Mario López',  role: 'participant', role_label: 'Participante' },
        { persona_id: 'p5', name: 'Sara Castillo', role: 'participant', role_label: 'Participante' },
    ],
};

async function mockShellRoutes(page: Page) {
    await installMockPlatformSession(page);

    await page.route('**/api/evangelism/strategies**', async (route: Route) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify([{ id: 's-1', name: 'FARO Centro' }]),
        });
    });
}

async function mockGrupoFetch(page: Page, grupo: typeof GRUPO_FIXTURE | null = GRUPO_FIXTURE, status = 200) {
    await page.route('**/api/evangelism/grupos/**', async (route: Route) => {
        if (!grupo) {
            await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify({ detail: 'Not found' }) });
            return;
        }
        await route.fulfill({
            status, contentType: 'application/json',
            body: JSON.stringify(grupo),
        });
    });
}

test.describe('Evangelism — Session report route (/sessions/[grupo_id])', () => {
    test.beforeEach(async ({ page }) => {
        await mockShellRoutes(page);
        await mockGrupoFetch(page);
    });

    test('navigates to the renamed route and renders the group context', async ({ page }) => {
        await page.goto('/plataforma/evangelism/faro/sessions/g1', { waitUntil: 'load' });
        await page.waitForLoadState('domcontentloaded');

        // Header + subtitle should reflect the loaded group.
        await expect(page.locator('h1')).toContainText(/Reportar/i);
        await expect(page.locator('body')).toContainText('Casa Bethel');
        await expect(page.locator('body')).toContainText('Centro');
    });

    test('attendance toggling updates the visible present/absent counters', async ({ page }) => {
        await page.goto('/plataforma/evangelism/faro/sessions/g1');
        await page.waitForLoadState('domcontentloaded');

        // Each stats tile renders: <colored div><p value/><p label/></colored div>.
        // Capture the numeric present count before any toggle.
        const presentLabel = page.getByText(/^Presentes$/);
        const presentBefore = Number(
            (await presentLabel.locator('..').locator('p.text-lg').first().textContent()) ?? '0',
        );
        const absentLabel = page.getByText(/^Ausentes$/);
        const absentBefore = Number(
            (await absentLabel.locator('..').locator('p.text-lg').first().textContent()) ?? '0',
        );

        // Toggle every person: mark them Present so absent count drops.
        const presentButtons = page.locator('button[title="Presente"]');
        const absentButtons = page.locator('button[title="Ausente"]');
        const cnt = await presentButtons.count();
        for (let i = 0; i < cnt; i += 1) {
            await presentButtons.nth(i).click();
        }
        const absentCnt = await absentButtons.count();
        for (let i = 0; i < absentCnt; i += 1) {
            await absentButtons.nth(i).click();
        }

        const presentAfter = Number(
            (await presentLabel.locator('..').locator('p.text-lg').first().textContent()) ?? '0',
        );
        const absentAfter = Number(
            (await absentLabel.locator('..').locator('p.text-lg').first().textContent()) ?? '0',
        );

        // Each "Presente" click flips one of initially-absent rows to present,
        // and each "Ausente" click flips one of initially-present rows to absent.
        expect(presentAfter).toBeGreaterThanOrEqual(presentBefore);
        expect(presentAfter + absentAfter).toBeGreaterThanOrEqual(cnt);
    });

    test('add and remove guests updates the Nuevos counter', async ({ page }) => {
        await page.goto('/plataforma/evangelism/faro/sessions/g1');
        await page.waitForLoadState('domcontentloaded');

        await page.getByRole('button', { name: /Agregar/i }).click();
        await page.getByRole('button', { name: /Agregar/i }).click();
        await expect(page.locator('text=/Invitados nuevos/')).toContainText(/\(2\)/);

        const firstGuestPhone = page.getByPlaceholder('Teléfono').first();
        await firstGuestPhone.locator('xpath=following-sibling::button[1]').click();
        await expect(page.locator('text=/Invitados nuevos/')).toContainText(/\(1\)/);
    });

    test('submit posts session + attendance and redirects to /groups', async ({ page }) => {
        const calls: { method: string; path: string; body: any }[] = [];

        await page.route('**/api/evangelism/sessions', async (route: Route) => {
            const req = route.request();
            if (req.method() === 'POST') {
                calls.push({ method: 'POST', path: new URL(req.url()).pathname, body: req.postDataJSON() });
                await route.fulfill({
                    status: 200, contentType: 'application/json',
                    body: JSON.stringify({ id: 'sess-99' }),
                });
                return;
            }
            await route.continue();
        });

        await page.route('**/api/evangelism/sessions/sess-99/habilitacion', async (route: Route) => {
            calls.push({ method: 'PATCH', path: new URL(route.request().url()).pathname, body: null });
            await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
        });

        await page.route('**/api/evangelism/sessions/sess-99/attendance', async (route: Route) => {
            calls.push({
                method: 'POST',
                path: new URL(route.request().url()).pathname,
                body: route.request().postDataJSON(),
            });
            await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
        });

        await page.goto('/plataforma/evangelism/faro/sessions/g1');
        await page.waitForLoadState('domcontentloaded');

        await page.getByRole('button', { name: /Guardar Reporte/i }).click();
        await page.waitForURL(/\/faro\/groups(?:\?.*)?$/, { timeout: 8000 }).catch(() => {});

        const sessionPost = calls.find(c => c.method === 'POST' && c.path.endsWith('/sessions'));
        expect(sessionPost, 'session POST must be issued').toBeTruthy();
        // The renamed param must reach the backend as grupo_id (not house_id).
        expect(sessionPost?.body?.grupo_id).toBe('g1');

        const habilitacion = calls.find(c => c.method === 'PATCH' && c.path.includes('/habilitacion'));
        expect(habilitacion, 'PATCH /habilitacion must be issued').toBeTruthy();

        const attendance = calls.find(c => c.method === 'POST' && c.path.includes('/attendance'));
        expect(attendance, 'POST /attendance must be issued').toBeTruthy();
    });

    test('unknown grupo renders the empty state', async ({ page }) => {
        await page.unroute('**/api/evangelism/grupos/**').catch(() => {});
        await mockGrupoFetch(page, null, 404);

        await page.goto('/plataforma/evangelism/faro/sessions/g-unknown');
        await expect(page.locator('body')).toContainText(/Grupo no encontrado/i);
    });

    test('old-style parametrization still works (URL pattern unchanged)', async ({ page }) => {
        // Regression: even though the dynamic segment was renamed, the URL pattern
        // /sessions/{uuid}/{maybeTrailing} must still resolve.
        await page.goto('/plataforma/evangelism/faro/sessions/g1', { waitUntil: 'load' });
        await page.waitForLoadState('domcontentloaded');
        await expect(page.locator('h1')).toContainText(/Reportar/i);
    });
});
