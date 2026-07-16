import { expect, test, type Page } from '@playwright/test';
import { installMockPlatformSession } from '../helpers/mockPlatformSession';

const PERSONA_ID = '241df55c-34aa-52f8-ba06-c252d9cf5d92';

const PERSONA_FIXTURE = {
  id: PERSONA_ID,
  nombre_completo: 'Abigail Monsalve',
  first_name: 'Abigail',
  last_name: 'Monsalve',
  email: 'abigail.monsalve@ccf.local',
  phone: '+57 300 123 4567',
  address: 'Cra 45 #12-33',
  status: 'Activa',
  church_role: 'Líder de Consolidación',
  xp: 420,
  level: 7,
  house: 'Faro Norte',
  joinedAt: '2024-01-15T00:00:00Z',
  birthday: '1996-08-14T00:00:00Z',
  pastoral_notes: 'Abigail Monsalve tiene potencial pastoral en su área de servicio. Su participación este mes es consistente.',
  current_mentorship: {
    id: 'mentorship-1',
    mentor_persona_id: 'mentor-1',
    mentor_name: 'Marta Salcedo',
    mentor_role: 'Pastora de Consolidación',
    mentee_persona_id: PERSONA_ID,
    mentee_name: 'Abigail Monsalve',
    mentee_role: 'Líder de Consolidación',
    notes: 'Seguimiento quincenal',
    status: 'active',
    started_at: '2026-06-01T00:00:00Z',
    ended_at: null,
  },
  mesh_insight: {
    title: 'MESH Insight',
    summary: 'Abigail Monsalve tiene potencial pastoral en su área de servicio. Su participación este mes es consistente.',
    recommendation: 'Reforzar mentoría y revisar próxima ruta de liderazgo.',
    health_score: 84,
    health_status: 'healthy',
    attendance_rate: 85,
    academy_progress: 65,
    volunteer_commitment: 92,
    metrics: [
      { key: 'attendance_rate', label: 'Asistencia Mensual', value: 85, display_value: '85%' },
      { key: 'academy_progress', label: 'Progreso Academia', value: 65, display_value: '65%' },
      { key: 'volunteer_commitment', label: 'Compromiso Voluntario', value: 92, display_value: '92%' },
    ],
    signals: ['Participación estable', 'Buena respuesta a mentoría'],
    current_mentorship: {
      mentor_persona_id: 'mentor-1',
      mentor_name: 'Marta Salcedo',
      mentor_role: 'Pastora de Consolidación',
    },
  },
};

async function installCrmPersonaDetailMocks(page: Page) {
  await installMockPlatformSession(page, {
    permissions: {
      'crm:read': 'allow',
      'crm:edit': 'allow',
      'crm:manage': 'allow',
    },
  });

  await page.route(`**/api/crm/personas/${PERSONA_ID}`, async (route) => {
    if (route.request().method() === 'PATCH') {
      const body = route.request().postDataJSON();
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ...PERSONA_FIXTURE, ...body }),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(PERSONA_FIXTURE),
    });
  });

  await page.route(`**/api/crm/personas/${PERSONA_ID}/timeline`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 'timeline-1',
          event_type: 'Seguimiento pastoral',
          notes: 'Se registró llamada de seguimiento y oración.',
          created_at: '2026-07-01T15:30:00Z',
        },
        {
          id: 'timeline-2',
          event_type: 'Asistencia registrada',
          notes: 'Asistió al encuentro semanal del Faro Norte.',
          created_at: '2026-07-08T19:00:00Z',
        },
      ]),
    });
  });

  await page.route(`**/api/crm/personas/${PERSONA_ID}/donations`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 'donation-1',
          donation_type: 'diezmo',
          amount: 120000,
          created_at: '2026-07-02T00:00:00Z',
        },
        {
          id: 'donation-2',
          donation_type: 'ofrenda',
          amount: 80000,
          created_at: '2026-07-09T00:00:00Z',
        },
      ]),
    });
  });

  await page.route(`**/api/crm/personas/${PERSONA_ID}/mentor-candidates**`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 'mentor-1',
          nombre_completo: 'Marta Salcedo',
          church_role: 'Pastora de Consolidación',
          fit_score: 96,
          fit_reason: 'Alta afinidad pastoral y seguimiento activo.',
        },
        {
          id: 'mentor-2',
          nombre_completo: 'Carlos Rueda',
          church_role: 'Supervisor',
          fit_score: 88,
          fit_reason: 'Buen acompañamiento y experiencia en discipulado.',
        },
      ]),
    });
  });

  await page.route(`**/api/crm/personas/${PERSONA_ID}/mentorship`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ ok: true }),
    });
  });

  await page.route('**/api/crm/colombian-departments', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        { id: 11, name: 'Bogotá D.C.' },
        { id: 5, name: 'Antioquia' },
      ]),
    });
  });
}

test.describe('CRM persona detail deep smoke', () => {
  test.beforeEach(async ({ page }) => {
    await installCrmPersonaDetailMocks(page);
  });

  test('renders persona overview with MESH insight', async ({ page }) => {
    await page.goto(`/plataforma/crm/personas/${PERSONA_ID}`, { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    await expect(page.getByRole('heading', { name: 'Abigail Monsalve' })).toBeVisible();
    await expect(page.locator('body')).toContainText(/MESH Insight/i);
    await expect(page.locator('body')).toContainText(/Asignar Mentoría/i);
    await expect(page.locator('body')).toContainText(/Asistencia Mensual/i);
    await expect(page.locator('body')).toContainText(/85%/i);
    await expect(page.locator('body')).toContainText(/Progreso Academia/i);
    await expect(page.locator('body')).toContainText(/Compromiso Voluntario/i);
  });

  test('loads timeline and donations tabs on demand', async ({ page }) => {
    await page.goto(`/plataforma/crm/personas/${PERSONA_ID}`, { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    await page.getByRole('button', { name: /Historial/i }).click();
    await expect(page.locator('body')).toContainText(/Línea de Tiempo Pastoral/i);
    await expect(page.locator('body')).toContainText(/Seguimiento pastoral/i);
    await expect(page.locator('body')).toContainText(/Asistencia registrada/i);

    await page.getByRole('button', { name: /Contribuciones/i }).click();
    await expect(page.locator('body')).toContainText(/Total Diezmos/i);
    await expect(page.locator('body')).toContainText(/Total Ofrendas/i);
    await expect(page.locator('body')).toContainText(/Historial de Siembras/i);
  });

  test('opens mentor drawer, loads candidates and saves mentorship', async ({ page }) => {
    let mentorshipSaved = false;

    await page.unroute(`**/api/crm/personas/${PERSONA_ID}/mentorship`);
    await page.route(`**/api/crm/personas/${PERSONA_ID}/mentorship`, async (route) => {
      mentorshipSaved = route.request().method() === 'POST';
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ok: true }),
      });
    });

    await page.goto(`/plataforma/crm/personas/${PERSONA_ID}`, { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    await page.getByRole('button', { name: /Asignar Mentoría/i }).first().click();
    await expect(page.locator('body')).toContainText(/Buscar mentor/i);
    await expect(page.locator('body')).toContainText(/Marta Salcedo/i);
    await page.getByRole('button', { name: /Carlos Rueda/i }).click();
    await page.getByRole('button', { name: /Guardar/i }).click();

    await expect.poll(() => mentorshipSaved).toBeTruthy();
  });
});
