import { expect, test, type Page } from '@playwright/test';
import { installMockPlatformSession } from '../helpers/mockPlatformSession';

const PROFILE_FIXTURE = {
  total_progress: 74,
  certificates_count: 1,
  active_courses: [
    {
      id: 'enrollment-1',
      progress_percent: 82,
      attendance_percent: 91,
      approved: false,
      course: {
        id: 'course-1',
        title: 'Ruta de Liderazgo Pastoral',
        modality: 'formal',
      },
    },
    {
      id: 'enrollment-2',
      progress_percent: 66,
      attendance_percent: 88,
      approved: false,
      course: {
        id: 'course-2',
        title: 'Cuidado Pastoral Integral',
        modality: 'non_formal',
      },
    },
  ],
};

const CERTIFICATES_FIXTURE = [
  {
    course_title: 'Doctrina Base',
    certificate_type: 'Aprobación',
    issued_at: '2026-06-15T00:00:00Z',
  },
];

const PROGRESS_FIXTURE = [
  {
    id: 'course-1',
    title: 'Ruta de Liderazgo Pastoral',
    progress_percent: 82,
    status: 'in_progress',
    average_grade: 94.2,
    lessons_completed: 9,
    total_lessons: 11,
    last_activity: '2026-07-10T14:00:00Z',
    certificate_issued: false,
  },
  {
    id: 'course-2',
    title: 'Cuidado Pastoral Integral',
    progress_percent: 100,
    status: 'completed',
    average_grade: 97.5,
    lessons_completed: 8,
    total_lessons: 8,
    last_activity: '2026-07-01T09:00:00Z',
    certificate_issued: true,
  },
];

async function installAcademyProfileMocks(page: Page) {
  await installMockPlatformSession(page, {
    role: 'lector',
    permissions: {
      'academy:read': 'allow',
      'academy:study': 'allow',
    },
  });

  await page.route('**/api/academy/me/profile', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(PROFILE_FIXTURE),
    });
  });

  await page.route('**/api/academy/me/certificates', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(CERTIFICATES_FIXTURE),
    });
  });

  await page.route('**/api/academy/me/progress', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(PROGRESS_FIXTURE),
    });
  });
}

test.describe('Academy profile deep smoke', () => {
  test.beforeEach(async ({ page }) => {
    await installAcademyProfileMocks(page);
  });

  test('renders academy profile overview with courses and certificates', async ({ page }) => {
    await page.goto('/plataforma/academy/profile', { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    await expect(page.locator('body')).toContainText(/Mi Perfil Pastoral/i);
    await expect(page.locator('body')).toContainText(/Discípulo Maduro/i);
    await expect(page.locator('body')).toContainText(/Progreso total: 74%/i);
    await expect(page.locator('body')).toContainText(/Ruta de Liderazgo Pastoral/i);
    await expect(page.locator('body')).toContainText(/Cuidado Pastoral Integral/i);
    await expect(page.locator('body')).toContainText(/Doctrina Base/i);
    await expect(page.locator('body')).toContainText(/Certificados/i);
  });

  test('switches profile view modes and keeps the academic summary stable', async ({ page }) => {
    await page.goto('/plataforma/academy/profile', { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    await page.getByRole('button', { name: /^Lista$/i }).click();
    await expect(page.locator('body')).toContainText(/Progreso 82% · Asistencia 91%/i);

    await page.getByRole('button', { name: /^Tabla$/i }).click();
    await expect(page.locator('body')).toContainText(/Ruta de Liderazgo Pastoral/i);
    await expect(page.locator('body')).toContainText(/82%/i);
  });

  test('renders progress detail with stats and alternate views', async ({ page }) => {
    await page.goto('/plataforma/academy/profile/progress', { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    await expect(page.locator('body')).toContainText(/Mi Progreso/i);
    await expect(page.locator('body')).toContainText(/Rendimiento Académico/i);
    await expect(page.locator('body')).toContainText(/Ruta de Liderazgo Pastoral/i);
    await expect(page.locator('body')).toContainText(/Cuidado Pastoral Integral/i);

    await page.getByRole('button', { name: /^Tabla$/i }).click();
    await expect(page.locator('body')).toContainText(/94.2/i);

    await page.getByRole('button', { name: /^Lista$/i }).click();
    await expect(page.locator('body')).toContainText(/9\/11 lecciones/i);
  });
});
