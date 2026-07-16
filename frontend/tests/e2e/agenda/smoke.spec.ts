import { defineAuthenticatedModuleRouteSmoke } from '../helpers/moduleRouteSmoke';

const AGENDA_ROUTES = [
  {
    id: 'calendar-root',
    path: '/plataforma/calendar',
    expectedText: /calendario|eventos visibles|pr[oó]ximos|cambiar vista/i,
  },
  {
    id: 'agenda-events',
    path: '/plataforma/agenda/events',
    expectedText: /agenda de iglesia|eventos sin seguimiento de asistencia|agenda completa/i,
  },
] as const;

defineAuthenticatedModuleRouteSmoke({
  suiteName: 'agenda/calendar critical smoke',
  tag: '@agenda',
  routes: AGENDA_ROUTES,
});
