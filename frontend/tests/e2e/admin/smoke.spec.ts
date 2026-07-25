import { defineAuthenticatedModuleRouteSmoke } from '../helpers/moduleRouteSmoke';
import { installAdminDataMocks } from '../helpers/adminDataMocks';

const ADMIN_ROUTES = [
  {
    id: 'admin-dashboard',
    path: '/plataforma/admin',
    expectedText: /gesti[oó]n central|tesorer[ií]a|personas|comandos de control|Tesorería Consolidada/i,
  },
  {
    id: 'admin-users',
    path: '/plataforma/admin/users',
    expectedText: /usuarios|ministeriales|gesti[oó]n de accesos|provisionar todos/i,
  },
  {
    id: 'admin-roles',
    path: '/plataforma/admin/roles',
    expectedText: /roles|gesti[oó]n de roles|matriz de permisos/i,
  },
  {
    id: 'admin-access',
    path: '/plataforma/admin/access',
    expectedText: /seguridad y accesos|roles ministeriales|auditor[ií]a de usuarios/i,
    // Allow non-critical timeouts from global providers (e.g. ConfigProvider) that
    // don't affect page content but may log console.error before the mock intercepts.
    allowedConsolePatterns: [/ApiError: Request timed out/i, /Failed to load resource/i],
  },
] as const;

defineAuthenticatedModuleRouteSmoke({
  suiteName: 'admin critical smoke',
  tag: '@admin',
  routes: ADMIN_ROUTES,
  onBeforeEach: [installAdminDataMocks],
});
