import { expect, test, type Page } from '@playwright/test';
import { installMockPlatformSession } from '../helpers/mockPlatformSession';

type RoleDefinition = {
  id: string;
  name: string;
};

type Persona = {
  id: string;
  nombre_completo: string;
  email: string;
  church_role?: string;
};

type MinistryEvent = {
  id: string;
  name: string;
  description: string;
  event_type: string;
  target_audience: 'ALL' | 'ROLE' | 'MANUAL';
  target_role_id?: string | null;
  target_role_ids: string[];
  target_persona_ids: string[];
  day_of_week?: number;
  start_time?: string;
  end_time?: string;
  status?: string;
  location?: string | null;
};

type EventDashboardStat = {
  event_id: string;
  latest_session: string | null;
  attended: number;
  expected: number;
  rate: number;
};

type SessionAssignment = {
  persona_id: string;
  role: string;
  persona_name?: string;
};

type SessionData = {
  event_id: string;
  session_date: string;
  assignments: SessionAssignment[];
  metrics: Record<string, number>;
  attendees: Array<{ persona_id: string; name: string; role: string; scanned_at: string | null }>;
  absentees: Array<{ persona_id: string; name: string; role: string; phone: string }>;
  total_absentees: number;
  absentees_truncated: boolean;
  total_attendance: number;
  total_expected: number;
  attendance_rate: number;
};

const ROLES: RoleDefinition[] = [
  { id: 'role-lider', name: 'Líder' },
  { id: 'role-jovenes', name: 'Jóvenes' },
  { id: 'role-ujieres', name: 'Ujieres' },
];

const PERSONAS: Persona[] = [
  { id: 'persona-abigail', nombre_completo: 'Abigail Monsalve', email: 'abigail@ccf.local', church_role: 'Jóvenes' },
  { id: 'persona-carlos', nombre_completo: 'Carlos Rueda', email: 'carlos@ccf.local', church_role: 'Líder' },
  { id: 'persona-lucia', nombre_completo: 'Lucía Vega', email: 'lucia@ccf.local', church_role: 'Ujieres' },
];

const BASE_EVENTS: MinistryEvent[] = [
  {
    id: 'event-1',
    name: 'Noche de Esperanza',
    description: 'Encuentro evangelístico del viernes.',
    event_type: 'SPECIAL',
    target_audience: 'ROLE',
    target_role_id: 'role-jovenes',
    target_role_ids: ['role-jovenes'],
    target_persona_ids: [],
    start_time: '18:00',
    end_time: '20:00',
    status: 'ACTIVE',
    location: 'Auditorio Norte',
  },
];

const EVENT_DETAILS = {
  'event-1': {
    id: 'event-1',
    name: 'Noche de Esperanza',
    description: 'Encuentro evangelístico del viernes.',
    event_date: '2026-07-17',
    location: 'Auditorio Norte',
    attendees_count: 1,
    status: 'ACTIVE',
    created_at: '2026-07-10T12:00:00Z',
  },
};

const ANALYTICS_DATA = {
  kpis: {
    historical_avg: 42,
    trend_percentage: 18,
    peak_month: {
      month: 'Junio',
      avg: 58,
    },
  },
  monthly_data: [
    { month: 'Abr', avg_attendance: 31 },
    { month: 'May', avg_attendance: 37 },
    { month: 'Jun', avg_attendance: 58 },
  ],
};

const TODAY = new Date().toISOString().split('T')[0];

async function installEvangelismEventsMocks(page: Page) {
  let eventsState = BASE_EVENTS.map((event) => ({ ...event, target_role_ids: [...(event.target_role_ids ?? [])], target_persona_ids: [...(event.target_persona_ids ?? [])] }));
  let statsState: EventDashboardStat[] = [
    { event_id: 'event-1', latest_session: TODAY, attended: 1, expected: 1, rate: 100 },
  ];
  let sessionState: Record<string, SessionData> = {
    [`event-1:${TODAY}`]: {
      event_id: 'event-1',
      session_date: TODAY,
      assignments: [],
      metrics: { Jóvenes: 1 },
      attendees: [{ persona_id: 'persona-abigail', name: 'Abigail Monsalve', role: 'Jóvenes', scanned_at: '2026-07-16T09:00:00Z' }],
      absentees: [],
      total_absentees: 0,
      absentees_truncated: false,
      total_attendance: 1,
      total_expected: 1,
      attendance_rate: 100,
    },
  };
  let nextEventId = 10;
  let lastAssignmentsPayload: { session_date: string; assignments: SessionAssignment[] } | null = null;

  const getPersonasForEvent = (event: MinistryEvent) => {
    if (event.target_audience === 'MANUAL') {
      return PERSONAS.filter((persona) => (event.target_persona_ids ?? []).includes(persona.id));
    }
    if (event.target_audience === 'ROLE') {
      const roleNames = (event.target_role_ids ?? [])
        .map((roleId) => ROLES.find((role) => role.id === roleId)?.name)
        .filter(Boolean);
      return PERSONAS.filter((persona) => roleNames.includes(persona.church_role ?? ''));
    }
    return PERSONAS;
  };

  const buildSessionState = (eventId: string, sessionDate: string): SessionData => {
    const event = eventsState.find((item) => item.id === eventId);
    const assignedPersonas = event ? getPersonasForEvent(event) : [];
    return (
      sessionState[`${eventId}:${sessionDate}`] ?? {
        event_id: eventId,
        session_date: sessionDate,
        assignments: [],
        metrics: assignedPersonas.reduce<Record<string, number>>((acc, persona) => {
          const key = persona.church_role || 'Persona';
          acc[key] = (acc[key] ?? 0) + 1;
          return acc;
        }, {}),
        attendees: [],
        absentees: assignedPersonas.map((persona) => ({
          persona_id: persona.id,
          name: persona.nombre_completo,
          role: persona.church_role || 'Persona',
          phone: '+57 300 000 0000',
        })),
        total_absentees: assignedPersonas.length,
        absentees_truncated: false,
        total_attendance: 0,
        total_expected: assignedPersonas.length,
        attendance_rate: 0,
      }
    );
  };

  await installMockPlatformSession(page, {
    role: 'admin',
    permissions: {
      'evangelism:read': 'allow',
      'evangelism:manage': 'allow',
      'crm:read': 'allow',
    },
  });

  await page.route('**/api/evangelism/strategies**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([{ id: 'strategy-1', name: 'FARO Centro' }]),
    });
  });

  await page.route('**/api/evangelism/roles**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(ROLES),
    });
  });

  await page.route('**/api/crm/personas**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(PERSONAS),
    });
  });

  await page.route('**/api/evangelism/scanner/validate/*', async (route) => {
    const token = route.request().url().split('/scanner/validate/')[1] ?? '';
    if (token === 'CCF-PER-VALID-ABIGAIL') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          valid: true,
          persona_id: 'persona-abigail',
          persona_name: 'Abigail Monsalve',
          role: 'Jóvenes',
        }),
      });
      return;
    }

    await route.fulfill({
      status: 400,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Token inválido' }),
    });
  });

  await page.route('**/api/evangelism/attendance/bulk', async (route) => {
    const body = route.request().postDataJSON() as { event_id: string; persona_ids: string[]; attendance_date: string };
    const event = eventsState.find((item) => item.id === body.event_id);
    const expectedUniverse = event ? getPersonasForEvent(event) : [];
    const attendees = expectedUniverse
      .filter((persona) => body.persona_ids.includes(persona.id))
      .map((persona) => ({
        persona_id: persona.id,
        name: persona.nombre_completo,
        role: persona.church_role || 'Persona',
        scanned_at: '2026-07-16T10:30:00Z',
      }));
    const absentees = expectedUniverse
      .filter((persona) => !body.persona_ids.includes(persona.id))
      .map((persona) => ({
        persona_id: persona.id,
        name: persona.nombre_completo,
        role: persona.church_role || 'Persona',
        phone: '+57 300 000 0000',
      }));

    sessionState[`${body.event_id}:${body.attendance_date}`] = {
      ...buildSessionState(body.event_id, body.attendance_date),
      attendees,
      absentees,
      total_attendance: attendees.length,
      total_expected: expectedUniverse.length,
      total_absentees: absentees.length,
      attendance_rate: expectedUniverse.length === 0 ? 0 : Math.round((attendees.length / expectedUniverse.length) * 100),
    };

    statsState = statsState.map((stat) =>
      stat.event_id === body.event_id
        ? {
            ...stat,
            latest_session: body.attendance_date,
            attended: attendees.length,
            expected: expectedUniverse.length,
            rate: expectedUniverse.length === 0 ? 0 : Math.round((attendees.length / expectedUniverse.length) * 100),
          }
        : stat,
    );

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ recorded: attendees.length, marked_absent: absentees.length }),
    });
  });

  await page.route('**/api/evangelism/events**', async (route) => {
    const method = route.request().method();
    const url = new URL(route.request().url());
    const rawPath = url.pathname.split('/api/evangelism/events')[1] ?? '';

    if (rawPath === '' || rawPath === '/') {
      if (method === 'POST') {
        const body = route.request().postDataJSON() as Omit<MinistryEvent, 'id'>;
        const createdEvent: MinistryEvent = {
          id: `event-${nextEventId++}`,
          name: body.name,
          description: body.description ?? '',
          event_type: body.event_type,
          target_audience: body.target_audience,
          target_role_id: body.target_role_id ?? null,
          target_role_ids: body.target_role_ids ?? [],
          target_persona_ids: body.target_persona_ids ?? [],
          day_of_week: body.day_of_week,
          start_time: body.start_time,
          end_time: body.end_time,
          status: 'ACTIVE',
          location: null,
        };
        eventsState = [createdEvent, ...eventsState];
        statsState = [
          { event_id: createdEvent.id, latest_session: null, attended: 0, expected: getPersonasForEvent(createdEvent).length, rate: 0 },
          ...statsState,
        ];
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
      return;
    }

    if (rawPath === '/dashboard-stats') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(statsState),
      });
      return;
    }

    if (rawPath.endsWith('/analytics')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(ANALYTICS_DATA),
      });
      return;
    }

    if (rawPath.endsWith('/assignments')) {
      lastAssignmentsPayload = route.request().postDataJSON() as { session_date: string; assignments: SessionAssignment[] };
      const eventId = rawPath.split('/')[1] ?? '';
      const sessionDate = lastAssignmentsPayload?.session_date ?? TODAY;
      const current = buildSessionState(eventId, sessionDate);
      const decoratedAssignments = (lastAssignmentsPayload?.assignments ?? []).map((assignment) => ({
        ...assignment,
        persona_name: PERSONAS.find((persona) => persona.id === assignment.persona_id)?.nombre_completo,
      }));
      sessionState[`${eventId}:${sessionDate}`] = {
        ...current,
        assignments: decoratedAssignments,
      };

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ok: true }),
      });
      return;
    }

    if (rawPath.includes('/sessions/') && rawPath.endsWith('/visitors')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ok: true }),
      });
      return;
    }

    if (rawPath.includes('/sessions/') && rawPath.endsWith('/export')) {
      await route.fulfill({
        status: 200,
        contentType: 'text/csv',
        body: 'name,role\nAbigail Monsalve,Jóvenes\n',
      });
      return;
    }

    if (rawPath.includes('/sessions/')) {
      const [, eventId, , sessionDate] = rawPath.split('/');
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(buildSessionState(eventId, sessionDate)),
      });
      return;
    }

    const eventId = rawPath.replace(/^\//, '').split('/')[0] ?? '';
    const detail = EVENT_DETAILS[eventId as keyof typeof EVENT_DETAILS];
    if (!detail) {
      await route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Event not found' }),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(detail),
    });
  });

  return {
    getLastAssignmentsPayload: () => lastAssignmentsPayload,
  };
}

test.describe('Evangelism events and scanner deep smoke', () => {
  test('creates a manual event and registers attendance through scanner mode', async ({ page }) => {
    await installEvangelismEventsMocks(page);

    await page.goto('/plataforma/evangelism/events', { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    await expect(page.locator('body')).toContainText(/Noche de Esperanza/i);
    await expect(page.locator('body')).toContainText(/1 \/ 1 \(100%\)/i);

    await page.getByRole('button', { name: /^Nuevo$/i }).click();
    await expect(page.locator('body')).toContainText(/Nuevo Evento/i);
    await page.getByPlaceholder(/Ej: Servicio Dominical/i).fill('Cumbre Juvenil');
    await page.locator('select').filter({ has: page.locator('option[value="MANUAL"]') }).first().selectOption('MANUAL');
    await page.getByPlaceholder(/Buscar por nombre, correo o rol/i).fill('Abigail');
    await page.getByRole('button', { name: /Agregar/i }).click();
    await page.locator('input[type="time"]').nth(0).fill('18:00');
    await page.locator('input[type="time"]').nth(1).fill('20:30');
    await page.getByRole('button', { name: /^Guardar$/i }).click();

    await expect(page.locator('body')).toContainText(/Cumbre Juvenil/i);
    await expect(page.locator('body')).toContainText(/Universo: 1/i);

    await page.getByRole('button', { name: /Panel de Asistencia/i }).first().click();
    await expect(page.locator('body')).toContainText(/Registro de Asistencia/i);

    await page.getByRole('button', { name: /Modo Escáner/i }).click();
    await page.getByPlaceholder(/CCF-PER-ID-XXXXXX/i).fill('CCF-PER-VALID-ABIGAIL');
    await page.getByRole('button', { name: /^Validar$/i }).click();
    await expect(page.locator('body')).toContainText(/1 \/ 1/i);
    await page.getByRole('button', { name: /Guardar asistencia/i }).click();

    await expect(page.locator('body')).toContainText(/Cumbre Juvenil/i);
    await expect(page.locator('body')).toContainText(/1 \/ 1 \(100%\)/i);
  });

  test('renders event detail, saves session agenda and loads analytics', async ({ page }) => {
    const mocks = await installEvangelismEventsMocks(page);

    await page.goto('/plataforma/evangelism/events/event-1', { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    await expect(page.locator('body')).toContainText(/Noche de Esperanza/i);
    await expect(page.locator('body')).toContainText(/Evento con seguimiento/i);

    await page.getByRole('button', { name: /Analítica/i }).click();
    await expect(page.locator('body')).toContainText(/Promedio Histórico/i);
    await expect(page.locator('body')).toContainText(/42/i);

    await page.getByRole('button', { name: /Configurar sesión/i }).click();
    await expect(page.locator('body')).toContainText(/Agenda de la reunión/i);
    await page.getByLabel(/Maestro de ceremonia/i).fill('Carlos');
    await page.getByRole('button', { name: /Carlos Rueda/i }).click();
    await expect(page.locator('body')).toContainText(/Tienes cambios sin guardar en la agenda/i);
    await page.getByRole('button', { name: /Guardar agenda/i }).click();
    await expect.poll(() => mocks.getLastAssignmentsPayload()).not.toBeNull();
    await expect.poll(() => mocks.getLastAssignmentsPayload()?.assignments[0]?.persona_id).toBe('persona-carlos');
  });

  test('validates scanner tokens from the standalone route and recovers after errors', async ({ page }) => {
    await installEvangelismEventsMocks(page);

    await page.goto('/plataforma/evangelism/scanner', { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    await expect(page.locator('body')).toContainText(/Escáner de Asistencia/i);
    await page.getByPlaceholder(/Ingresar Token Manualmente/i).fill('CCF-PER-INVALIDO');
    await page.getByRole('button', { name: /Validar Token/i }).click();
    await expect(page.locator('body')).toContainText(/Buscando Código/i);

    await page.getByPlaceholder(/Ingresar Token Manualmente/i).fill('CCF-PER-VALID-ABIGAIL');
    await page.getByRole('button', { name: /Validar Token/i }).click();
    await expect(page.locator('body')).toContainText(/Abigail Monsalve/i);
    await expect(page.locator('body')).toContainText(/VALIDADO/i);
    await page.getByRole('button', { name: /Escanear Siguiente/i }).click();
    await expect(page.locator('body')).toContainText(/Buscando Código/i);
  });
});
