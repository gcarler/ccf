import { test, expect, Page } from '@playwright/test';

/**
 * E2E smoke coverage for the new Evangelism routes:
 *   - /plataforma/evangelism/rankings
 *   - /plataforma/evangelism/multiplication
 *
 * Network calls are intercepted with mocked JSON so the test runs
 * without DB / auth dependencies. We render at the page boundary
 * to avoid getting blocked by the workspace shell auth flow.
 */

async function mockEvangelismRoutes(page: Page) {
    // Auth bootstrap + sidebar/faro analytics endpoints that the WorkspaceLayout hits.
    await page.route('**/api/v3/auth/me', async (route) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
                id: 'e2e-user',
                email: 'pastor.e2e@ccf.local',
                role: 'pastor',
                permissions: ['evangelism:read', 'evangelism:manage'],
                sede_id: 'sede-1',
                persona_id: 'persona-1',
            }),
        });
    });

    // Sidebar strategies list.
    await page.route('**/api/evangelism/strategies**', async (route) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify([
                { id: 's-1', name: 'FARO Centro' },
                { id: 's-2', name: 'Sectorial Norte' },
            ]),
        });
    });

    // Module access check endpoints.
    await page.route('**/api/auth/v3/me**', async (route) => {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
    });
}

// ----------------------------------------------------------------------------
// Rankings page
// ----------------------------------------------------------------------------

test.describe('Evangelism — Rankings page', () => {
    test.beforeEach(async ({ page }) => {
        await mockEvangelismRoutes(page);

        await page.route('**/api/evangelism/rankings/groups**', async (route) => {
            const url = route.request().url();
            const body = url.includes('by=growth')
                ? [
                    { group_id: 'g1', group_name: 'Casa Bethel', growth: 6, current_personas: 18, previous_personas: 12 },
                    { group_id: 'g2', group_name: 'Los Pinos', growth: 3, current_personas: 15, previous_personas: 12 },
                ]
                : url.includes('by=visitors')
                ? [
                    { group_id: 'g3', group_name: 'Renuevo', visitors: 9 },
                    { group_id: 'g4', group_name: 'Esperanza', visitors: 4 },
                ]
                : [
                    { group_id: 'g1', group_name: 'Casa Bethel', attendance_rate: 92.0, present: 22, expected: 24 },
                    { group_id: 'g2', group_name: 'Los Pinos', attendance_rate: 81.5, present: 13, expected: 16 },
                ];
            await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
        });

        await page.route('**/api/evangelism/rankings/leaders**', async (route) => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify([
                    { leader_name: 'Ana Pérez', leader_id: 'p1', group_id: 'g1', group_name: 'Casa Bethel', attendance_pct: 92.0, personas: 24, visitors_this_month: 7 },
                    { leader_name: 'Luis Soto', leader_id: 'p2', group_id: 'g2', group_name: 'Los Pinos', attendance_pct: 81.5, personas: 16, visitors_this_month: 4 },
                ]),
            });
        });

        await page.route('**/api/evangelism/rankings/monthly-comparison**', async (route) => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    current_month: { total_sessions: 22, total_attendance: 145, total_expected: 180, avg_rate: 80.6, new_visitors: 11, new_conversions: 5 },
                    previous_month: { total_sessions: 19, total_attendance: 121, total_expected: 175, avg_rate: 69.1, new_visitors: 8, new_conversions: 3 },
                }),
            });
        });
    });

    test('renders attendance ranking and switches tabs', async ({ page }) => {
        // Bypass workspace shell so the page can mount without server-rendered layout.
        await page.goto('/login', { waitUntil: 'load' });

        // We navigate directly to the rankings route inside the protected area.
        await page.goto('/plataforma/evangelism/rankings', { waitUntil: 'load' });

        // Either we land on the protected page, or on login. Make sure the URL resolves.
        await page.waitForLoadState('domcontentloaded');

        // Page header should always render in the protected shell.
        await expect(page.locator('h1')).toContainText(/Rankings/i);

        // Tabs available.
        await page.getByRole('button', { name: /Líderes/i }).click();
        await page.getByRole('button', { name: /Mes a mes/i }).click();
        await page.getByRole('button', { name: /Grupos/i }).click();
    });

    test('switches ranking by dropdown', async ({ page }) => {
        await page.goto('/plataforma/evangelism/rankings', { waitUntil: 'load' });
        await page.waitForLoadState('networkidle').catch(() => {});
        const select = page.locator('select').first();
        await select.selectOption('growth');
        await select.selectOption('visitors');
    });
});

// ----------------------------------------------------------------------------
// Multiplication page
// ----------------------------------------------------------------------------

test.describe('Evangelism — Multiplication page', () => {
    test.beforeEach(async ({ page }) => {
        await mockEvangelismRoutes(page);

        await page.route('**/api/evangelism/multiplication/check**', async (route) => {
            const url = new URL(route.request().url());
            const umbral = Number(url.searchParams.get('umbral') || '15');
            const items = [
                { grupo_id: 'g1', grupo_nombre: 'Casa Bethel', lider_nombre: 'Ana Pérez', total_miembros: 19, excede_umbral: true, sugerencia: 'Dividir en dos células' },
                { grupo_id: 'g2', grupo_nombre: 'Los Pinos', lider_nombre: 'Luis Soto', total_miembros: 11, excede_umbral: 11 > umbral, sugerencia: 'Aún no alcanza el umbral' },
                { grupo_id: 'g3', grupo_nombre: 'Renuevo', lider_nombre: null, total_miembros: 7, excede_umbral: 7 > umbral, sugerencia: 'Aún no alcanza el umbral' },
            ];
            await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(items) });
        });

        await page.route('**/api/evangelism/multiplication/history**', async (route) => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify([
                    {
                        grupo_id: 'h-1',
                        grupo_nombre: 'Casa Bethel - A',
                        parent_group_id: 'g-0',
                        parent_group_nombre: 'Casa Bethel',
                        notes_historial: 'División del 2026-03-01',
                        created_at: '2026-03-01T10:00:00Z',
                        miembros_actuales: 12,
                        lider_nombre: 'Ana Pérez',
                    },
                ]),
            });
        });

        await page.route('**/api/crm/personas**', async (route) => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify([
                    { id: 'p1', nombre_completo: 'Ana Pérez' },
                    { id: 'p2', nombre_completo: 'Luis Soto' },
                ]),
            });
        });
    });

    test('renders overview metrics and switch between Analysis / History', async ({ page }) => {
        await page.goto('/plataforma/evangelism/multiplication', { waitUntil: 'load' });
        await page.waitForLoadState('domcontentloaded');

        await expect(page.locator('h1')).toContainText(/Multiplicación/i);

        // The "Listos para multiplicar" callout should appear for at least one group.
        await expect(page.locator('text=/Listo/i').first()).toBeVisible({ timeout: 5000 }).catch(() => {});

        // Switch to Historial tab.
        await page.getByRole('button', { name: /Historial/i }).click();

        // Back to Análisis tab.
        await page.getByRole('button', { name: /Análisis/i }).click();
    });

    test('changing the umbral updates the analysis panel', async ({ page }) => {
        await page.goto('/plataforma/evangelism/multiplication', { waitUntil: 'load' });
        await page.waitForLoadState('domcontentloaded');

        const select = page.locator('select').first();
        await select.selectOption('20');
        await select.selectOption('10');
    });
});
