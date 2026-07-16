import { expect, test, type Page } from '@playwright/test';
import { installMockPlatformSession } from '../helpers/mockPlatformSession';

type AgendaEventRecord = {
  id: number;
  title: string;
  description?: string | null;
  start_at: string;
  end_at?: string | null;
  location?: string | null;
  is_all_day: boolean;
};

const INITIAL_EVENTS: AgendaEventRecord[] = [
  {
    id: 301,
    title: 'Reunión de liderazgo',
    description: 'Planeación semanal del equipo pastoral.',
    start_at: '2026-07-20T00:00:00.000Z',
    end_at: '2026-07-20T23:59:59.000Z',
    location: 'Salón principal',
    is_all_day: true,
  },
  {
    id: 302,
    title: 'Oración de voluntarios',
    description: 'Cobertura previa al servicio.',
    start_at: '2026-07-22T00:00:00.000Z',
    end_at: '2026-07-22T23:59:59.000Z',
    location: 'Capilla',
    is_all_day: true,
  },
];

async function installAgendaDeepMocks(page: Page) {
  let eventsState = INITIAL_EVENTS.map((event) => ({ ...event }));
  let nextEventId = 400;

  const buildCalendarItems = () =>
    eventsState.map((event) => ({
      id: `agenda-${event.id}`,
      title: event.title,
      start: event.start_at,
      end: event.end_at,
      type: 'agenda_event',
      allDay: event.is_all_day,
      href: `/plataforma/agenda/events/${event.id}`,
      location: event.location,
    }));

  const findEvent = (eventId: number) => eventsState.find((event) => event.id === eventId);

  await installMockPlatformSession(page, {
    role: 'admin',
    permissions: {
      'spiritual_life:read': 'allow',
      'spiritual_life:edit': 'allow',
    },
  });

  await page.route('**/api/agenda/events/by-date-range**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(eventsState),
    });
  });

  await page.route('**/api/agenda/events', async (route) => {
    const method = route.request().method();

    if (method === 'POST') {
      const body = route.request().postDataJSON() as Omit<AgendaEventRecord, 'id'>;
      const createdEvent: AgendaEventRecord = {
        id: nextEventId++,
        title: body.title,
        description: body.description ?? null,
        start_at: body.start_at,
        end_at: body.end_at ?? null,
        location: body.location ?? null,
        is_all_day: body.is_all_day ?? true,
      };
      eventsState = [createdEvent, ...eventsState];
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(createdEvent),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(eventsState),
    });
  });

  await page.route('**/api/agenda/events/*', async (route) => {
    const eventId = Number(route.request().url().split('/agenda/events/')[1]?.split('?')[0]);
    const current = findEvent(eventId);

    if (!current) {
      await route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Event not found' }),
      });
      return;
    }

    const method = route.request().method();

    if (method === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(current),
      });
      return;
    }

    if (method === 'PUT') {
      const body = route.request().postDataJSON() as Partial<AgendaEventRecord>;
      const updatedEvent: AgendaEventRecord = {
        ...current,
        ...body,
        id: current.id,
      };
      eventsState = eventsState.map((event) => (event.id === eventId ? updatedEvent : event));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(updatedEvent),
      });
      return;
    }

    if (method === 'DELETE') {
      eventsState = eventsState.filter((event) => event.id !== eventId);
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ok: true }),
      });
      return;
    }

    await route.fulfill({
      status: 405,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Method not allowed' }),
    });
  });

  await page.route('**/api/system/calendar?view=*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(buildCalendarItems()),
    });
  });
}

test.describe('Agenda and calendar deep smoke', () => {
  test.beforeEach(async ({ page }) => {
    await installAgendaDeepMocks(page);
  });

  test('creates, edits and deletes manual agenda events from the owner module', async ({ page }) => {
    await page.goto('/plataforma/agenda/events', { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    await expect(page.locator('body')).toContainText(/Agenda de iglesia/i);
    await expect(page.locator('body')).toContainText(/Reunión de liderazgo/i);
    await expect(page.locator('body')).toContainText(/Oración de voluntarios/i);

    await page.getByPlaceholder(/Reunión de liderazgo/i).fill('Encuentro de consolidación');
    const createDateInputs = page.locator('input[type="date"]');
    await createDateInputs.nth(0).fill('2026-07-24');
    await createDateInputs.nth(1).fill('2026-07-24');
    await page.getByRole('button', { name: /Crear evento/i }).click();

    await expect(page.locator('body')).toContainText(/Encuentro de consolidación/i);
    await expect(page.locator('body')).toContainText(/3 eventos visibles/i);

    const createdArticle = page.locator('article').filter({ hasText: 'Encuentro de consolidación' }).first();
    await createdArticle.getByRole('button', { name: /^Editar$/i }).click();
    const editingArticle = page.locator('article').filter({ hasText: /Edición rápida/ }).first();
    const editTitleInput = editingArticle.locator('input').first();
    await editTitleInput.fill('Encuentro de consolidación semanal');
    await editingArticle.getByRole('button', { name: /^Guardar$/i }).click();

    await expect(page.locator('body')).toContainText(/Encuentro de consolidación semanal/i);

    const updatedArticle = page.locator('article').filter({ hasText: 'Encuentro de consolidación semanal' }).first();
    await updatedArticle.getByRole('button', { name: /^Eliminar$/i }).click();
    await expect(page.locator('body')).not.toContainText(/Encuentro de consolidación semanal/i);
    await expect(page.locator('body')).toContainText(/2 eventos visibles/i);
  });

  test('edits the event detail screen and keeps the shared calendar contract aligned', async ({ page }) => {
    await page.goto('/plataforma/agenda/events/301', { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    await expect(page.locator('body')).toContainText(/Reunión de liderazgo/i);
    await expect(page.locator('body')).toContainText(/Sin cambios/i);

    await page.locator('input[value="Reunión de liderazgo"]').fill('Reunión de liderazgo ampliada');
    await page.locator('input').last().fill('Auditorio central');
    await page.locator('textarea').first().fill('Planeación trimestral con líderes de área.');

    await expect(page.locator('body')).toContainText(/Cambios pendientes/i);
    await page.getByRole('button', { name: /Guardar cambios/i }).click();
    await expect(page.locator('body')).toContainText(/Sin cambios/i);
    await expect(page.locator('body')).toContainText(/Reunión de liderazgo ampliada/i);

    await page.goto('/plataforma/calendar', { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    await expect(page.locator('body')).toContainText(/Próximos/i);
    await expect(page.locator('body')).toContainText(/Reunión de liderazgo ampliada/i);
  });

  test('navigates from the shared calendar back to the owning agenda detail route', async ({ page }) => {
    await page.goto('/plataforma/calendar', { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    await expect(page.locator('body')).toContainText(/Cambiar vista/i);
    await expect(page.locator('body')).toContainText(/Reunión de liderazgo/i);

    await page.locator('text=Reunión de liderazgo').first().click();
    await expect(page).toHaveURL(/\/plataforma\/agenda\/events\/301$/);
    await expect(page.locator('body')).toContainText(/Reunión de liderazgo/i);
  });
});
