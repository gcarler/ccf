import { defineAuthenticatedModuleRouteSmoke } from './helpers/moduleRouteSmoke';

const CRITICAL_ROUTES = [
  {
    id: 'crm-personas',
    path: '/plataforma/crm/personas',
    expectedText: /personas|directorio|miembros|consolidaci[oó]n/i,
  },
  {
    id: 'projects-root',
    path: '/plataforma/projects',
    expectedText: /proyectos|tareas|kanban|pipeline/i,
  },
  {
    id: 'evangelism-root',
    path: '/plataforma/evangelism',
    expectedText: /evangelismo|estrategias|faro|grupos/i,
  },
  {
    id: 'academy-root',
    path: '/plataforma/academy',
    expectedText: /academia|coach|curriculum|cursos/i,
  },
  {
    id: 'cms-root',
    path: '/plataforma/cms',
    expectedText: /cms|p[aá]ginas|builder|seo|contenido/i,
  },
];

defineAuthenticatedModuleRouteSmoke({
  suiteName: 'platform critical routes',
  tag: '@platform',
  routes: CRITICAL_ROUTES,
});
