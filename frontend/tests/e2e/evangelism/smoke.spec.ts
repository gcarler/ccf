import { defineAuthenticatedModuleRouteSmoke } from '../helpers/moduleRouteSmoke';

const EVANGELISM_ROUTES = [
  {
    id: 'evangelism-root',
    path: '/plataforma/evangelism',
    expectedText: /evangelismo|estrategias|faro|grupos/i,
  },
  {
    id: 'evangelism-groups',
    path: '/plataforma/evangelism/groups',
    expectedText: /grupos|faro|estrategia|lider/i,
  },
  {
    id: 'evangelism-rankings',
    path: '/plataforma/evangelism/rankings',
    expectedText: /rankings|lideres|grupos|comparaci[oó]n/i,
  },
] as const;

defineAuthenticatedModuleRouteSmoke({
  suiteName: 'evangelism critical smoke',
  tag: '@evangelism',
  routes: EVANGELISM_ROUTES,
});
