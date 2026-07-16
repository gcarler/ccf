import { defineAuthenticatedModuleRouteSmoke } from '../helpers/moduleRouteSmoke';

const CMS_ROUTES = [
  {
    id: 'cms-dashboard',
    path: '/plataforma/cms',
    expectedText: /cms|media|builder|paginas|contenido/i,
  },
  {
    id: 'cms-pages',
    path: '/plataforma/cms/pages',
    expectedText: /cms pages|paginas|seo|builder|publicad/i,
  },
  {
    id: 'cms-media',
    path: '/plataforma/cms/media',
    expectedText: /media|archivos|imagenes|biblioteca/i,
  },
] as const;

defineAuthenticatedModuleRouteSmoke({
  suiteName: 'cms critical smoke',
  tag: '@cms',
  routes: CMS_ROUTES,
});
