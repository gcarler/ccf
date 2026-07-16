import { defineAuthenticatedModuleRouteSmoke } from '../helpers/moduleRouteSmoke';

const PROJECTS_ROUTES = [
  {
    id: 'projects-list',
    path: '/plataforma/projects/list#projects-list',
    expectedText: /proyectos|centro de comando|nuevo proyecto|no hay proyectos/i,
  },
  {
    id: 'projects-tasks',
    path: '/plataforma/projects/tasks?view=list',
    expectedText: /proyectos|tareas|estado|prioridad|no hay tareas/i,
  },
  {
    id: 'projects-inbox',
    path: '/plataforma/projects/inbox?view=list',
    expectedText: /proyectos|inbox|respuestas|todo|menciones|inbox vac[ií]o/i,
  },
] as const;

defineAuthenticatedModuleRouteSmoke({
  suiteName: 'projects critical smoke',
  tag: '@projects',
  routes: PROJECTS_ROUTES,
});
