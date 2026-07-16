import { defineAuthenticatedModuleRouteSmoke } from '../helpers/moduleRouteSmoke';

const CRM_ROUTES = [
  {
    id: 'crm-dashboard',
    path: '/plataforma/crm',
    expectedText: /crm|pastoral|pipeline|directorio|personas/i,
  },
  {
    id: 'crm-personas',
    path: '/plataforma/crm/personas',
    expectedText: /personas|directorio|miembros|consolidaci[oó]n/i,
  },
  {
    id: 'crm-pipeline',
    path: '/plataforma/crm/pipeline',
    expectedText: /pipeline|consolidaci[oó]n|etapa|caso/i,
  },
] as const;

defineAuthenticatedModuleRouteSmoke({
  suiteName: 'crm critical smoke',
  tag: '@crm',
  routes: CRM_ROUTES,
});
