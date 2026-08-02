// F-02 (2026-08-02) — E2E: un Manager con sede abriendo un curso GLOBAL
// (sede_id NULL) debe ver el empty-state explicativo de la consola de gestión
// ("Sin estudiantes inscritos / Este curso es global...") en lugar de un error
// ("No se pudieron cargar los estudiantes" / "Curso no disponible").
//
// Escenario real (verificado en backend/api/academy.py course_students):
//   GET /academy/courses/{id}                          → 200 + curso con sede_id: null
//   GET /academy/admin/courses/{id}/students           → 200 + [] (scope admin
//     estricto Axioma-3: el Manager con sede NO ve UGC de cursos globales).
//
// Patrón de mocks de API sin backend real (igual que profile-detail.spec.ts):
// se simulan (1) la sesión staff con sede (role coordinador + academy:manage),
// (2) el detalle del curso global, (3) el listado de estudiantes 200+[]. El
// runtime Next vivo sirve la página. Ejecutar con el runner administrado:
//   node scripts/run-managed-playwright.mjs tests/e2e/academy/course-global-empty-state.spec.ts

import { expect, test, type Page } from '@playwright/test';
import { installMockPlatformSession } from '../helpers/mockPlatformSession';

const GLOBAL_COURSE_ID = '11111111-1111-4111-8111-111111111111';

// Fixture espejo de _serialize_course (backend/api/academy.py): sede_id null =
// curso global legítimo (H-01). Sólo importan para la UI: id, title, code,
// modality, cohort_name, lesson_count, sede_id.
const GLOBAL_COURSE_FIXTURE = {
  id: GLOBAL_COURSE_ID,
  code: 'GLO-E2E-001',
  slug: 'ruta-global-e2e',
  title: 'Ruta Global E2E',
  description: 'Curso global para E2E.',
  excerpt: 'Curso global',
  tag: 'global',
  cta_text: 'Inscribirme',
  syllabus: null,
  modality: 'non_formal',
  sede_id: null, // ← H-01: NULL = curso global legítimo (no un error)
  is_published: true,
  is_self_paced: true,
  duration_hours: 8,
  cohort_name: 'Cohorte Global 2026',
  certificate_type: null,
  xp_per_lesson: 0,
  access_level: 'persona',
  image_url: null,
  instructor_name: null,
  created_at: '2026-01-01T00:00:00Z',
  lesson_count: 0,
  total_minutes: 0,
  lessons: [],
};

async function installGlobalCourseMocks(page: Page) {
  // Manager con sede: role coordinador (auth_users.sede_id es NOT NULL — todo
  // usuario staff tiene sede; no existe "superadmin sin sede").
  await installMockPlatformSession(page, {
    role: 'coordinador',
    permissions: {
      'academy:read': 'allow',
      'academy:edit': 'allow',
      'academy:manage': 'allow',
    },
  });

  await page.route(`**/api/academy/courses/${GLOBAL_COURSE_ID}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(GLOBAL_COURSE_FIXTURE),
    });
  });

  // F-02: 200 + [] legítimo (scope admin estricto) — NO es un error y la UI no
  // debe mostrarlo como tal (ni como 500 con "Reintentar" ni como "Curso no
  // disponible").
  await page.route(`**/api/academy/admin/courses/${GLOBAL_COURSE_ID}/students`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    });
  });
}

test.describe('Academy — curso global + Manager con sede (F-02) @academy', () => {
  test.beforeEach(async ({ page }) => {
    await installGlobalCourseMocks(page);
  });

  test('muestra el empty-state explicativo del curso global, no un error', async ({ page }) => {
    await page.goto(`/plataforma/academy/courses/${GLOBAL_COURSE_ID}/manage`, {
      waitUntil: 'load',
    });
    await page.waitForLoadState('domcontentloaded');

    // El curso global carga (título visible) y el contador de alumnos es 0.
    await expect(page.locator('body')).toContainText(/Ruta Global E2E/i);
    await expect(page.locator('body')).toContainText(/0 Alumnos/i);

    // Empty-state explicativo de curso global (F-02): la lista vacía es
    // intencional, no un error.
    await expect(page.locator('body')).toContainText(/Sin estudiantes inscritos/i);
    await expect(page.locator('body')).toContainText(/Este curso es global/i);
    await expect(page.locator('body')).toContainText(/intencional, no un error/i);

    // Y NO debe verse ningún estado de error ni el muro de "Acceso Restringido":
    // ni el título de error retryable, ni el botón "Reintentar" (sólo la vista
    // grid de error lo renderiza), ni el 404 cross-sede, ni el muro staff.
    await expect(page.locator('body')).not.toContainText(/No se pudieron cargar los estudiantes/i);
    await expect(page.locator('body')).not.toContainText(/Reintentar/i);
    await expect(page.locator('body')).not.toContainText(/Curso no disponible/i);
    await expect(page.locator('body')).not.toContainText(/Acceso Restringido/i);
  });
});
