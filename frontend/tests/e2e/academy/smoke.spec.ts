import { defineAuthenticatedModuleRouteSmoke } from '../helpers/moduleRouteSmoke';

const ACADEMY_ROUTES = [
  {
    id: 'academy-dashboard',
    path: '/plataforma/academy',
    expectedText: /academia|coach|curriculum|cursos/i,
  },
  {
    id: 'academy-forum',
    path: '/plataforma/academy/forum',
    expectedText: /foro|discusi[oó]n|hilo|academia/i,
  },
  {
    id: 'academy-coordination',
    path: '/plataforma/academy/coordination',
    expectedText: /coordinaci[oó]n|alistamiento|programa|cursos/i,
  },
] as const;

defineAuthenticatedModuleRouteSmoke({
  suiteName: 'academy critical smoke',
  tag: '@academy',
  routes: ACADEMY_ROUTES,
});
