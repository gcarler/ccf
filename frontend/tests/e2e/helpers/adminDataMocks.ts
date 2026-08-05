import type { Page, Route } from '@playwright/test';

/**
 * Installs route interceptors for the 4 data endpoints consumed by the admin
 * dashboard page, so the SPA renders its full content instead of hanging in
 * the loading/"Verificando Sistemas…" state.
 *
 * Usage from a beforeEach hook:
 *   await installAdminDataMocks(page);
 */
export async function installAdminDataMocks(page: Page) {
  // Admin dashboard endpoints
  await page.route('**/api/admin/testimonials**', handleTestimonials);
  await page.route('**/api/agents/tasks**', handleAgentTasks);
  await page.route('**/api/agents/insights**', handleAgentInsights);
  await page.route('**/api/admin/stats**', handleAdminStats);

  // Admin access/roles/users endpoints — use regex for unambiguous matching
  await page.route(/\/api\/admin\/roles/, handleAdminRoles);
  await page.route(/\/api\/admin\/users\/?(?!.*permissions)/, handleAdminUsers);
  await page.route(/\/api\/admin\/users\/.+\/permissions/, handleAdminUserPermissions);
  await page.route(/\/api\/admin\/permissions$/, handleAdminPermissions);

  // Workspace config — the ConfigProvider fetches this on mount
  await page.route(/\/api\/workspace\/config/, handleWorkspaceConfig);
}

// ── Mock handlers ──────────────────────────────────────────────────────────

async function handleTestimonials(route: Route) {
  if (route.request().method() !== 'GET') {
    return route.continue();
  }
  await route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify([
      {
        id: 1,
        title: 'Sanidad Divina',
        content:
          'Dios me sanó de una enfermedad crónica después de 10 años. ¡Gloria a Dios!',
        is_approved: false,
        author: 'María G.',
        created_at: '2026-07-20T10:30:00Z',
      },
      {
        id: 2,
        title: 'Restauración Familiar',
        content:
          'Nuestra familia fue restaurada después de años de conflicto. Dios obró un milagro.',
        is_approved: true,
        author: 'Carlos R.',
        created_at: '2026-07-18T14:00:00Z',
      },
      {
        id: 3,
        title: 'Provisión Milagrosa',
        content:
          'En medio de la crisis económica, Dios proveyó exactamente lo que necesitábamos.',
        is_approved: false,
        author: 'Ana L.',
        created_at: '2026-07-22T08:15:00Z',
      },
    ]),
  });
}

async function handleAgentTasks(route: Route) {
  if (route.request().method() !== 'GET') {
    return route.continue();
  }
  await route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify([
      {
        id: 'task-001',
        title: 'Revisión de Cuentas de Tesorería',
        description:
          'Conciliación pendiente del cierre mensual de Julio. Revisar discrepancias en donaciones.',
        priority: 'high',
        status: 'Activo',
      },
      {
        id: 'task-002',
        title: 'Auditoría de Roles Ministeriales',
        description:
          'Verificar que todos los líderes tengan asignados los permisos correctos en el CRM.',
        priority: 'medium',
        status: 'Activo',
      },
      {
        id: 'task-003',
        title: 'Aprobación de Nuevos Miembros',
        description:
          '5 solicitudes de membresía pendientes de revisión y aprobación.',
        priority: 'medium',
        status: 'Activo',
      },
      {
        id: 'task-004',
        title: 'Cache de Contenido CMS',
        description:
          'El CDN no ha purgado la última versión de la página de inicio. Reprogramar purga.',
        priority: 'low',
        status: 'Activo',
      },
    ]),
  });
}

async function handleAgentInsights(route: Route) {
  if (route.request().method() !== 'GET') {
    return route.continue();
  }
  await route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify([
      {
        id: 'insight-001',
        title: 'Pico de Donaciones Detectado',
        insight_type: 'financial_alert',
        payload:
          'Se registró un incremento del 23% en donaciones durante la última semana, correlacionado con la campaña de evangelismo digital.',
      },
      {
        id: 'insight-002',
        title: 'Tendencia de Crecimiento',
        insight_type: 'growth_metric',
        payload:
          'La asistencia a grupos de casa creció un 15% este trimestre. Considerar apertura de 2 nuevos grupos.',
      },
      {
        id: 'insight-003',
        title: 'Rendimiento de Base de Datos',
        insight_type: 'system_health',
        payload:
          'Los tiempos de consulta del módulo de membresía superan el umbral recomendado. Optimizar índices.',
      },
    ]),
  });
}

async function handleAdminStats(route: Route) {
  if (route.request().method() !== 'GET') {
    return route.continue();
  }
  await route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      donaciones_mes: 45820.5,
      diezmos_mes: 32100.0,
      ofrendas_mes: 13720.5,
      personas: 1247,
      personas_nuevas_mes: 38,
      usuarios_activos: 892,
    }),
  });
}

// ── Admin Access / Roles / Users mocks ────────────────────────────────────

async function handleAdminRoles(route: Route) {
  const method = route.request().method();

  // POST /admin/roles — create role (the access page creates new roles)
  if (method === 'POST') {
    // Return a mock created role — the page calls fetchData again after creation.
    const body = route.request().postDataJSON?.() || {};
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: `mock-role-${Date.now()}`,
        nombre: body.nombre || 'Nuevo Rol',
        permisos: body.permisos || {},
        users_count: 0,
      }),
    });
    return;
  }

  // PATCH /admin/roles/:id — update permissions (the drawer save)
  if (method === 'PATCH') {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'ok' }),
    });
    return;
  }

  // GET /admin/roles — list roles
  if (method !== 'GET') {
    return route.continue();
  }

  await route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      items: [
        {
          id: 'role-admin',
          nombre: 'ADMINISTRADOR',
          permisos: {
            'admin:read': 'allow',
            'admin:edit': 'allow',
            'admin:manage': 'allow',
            'crm:read': 'allow',
            'crm:edit': 'allow',
            'crm:manage': 'allow',
            'academy:read': 'allow',
            'academy:edit': 'allow',
            'academy:manage': 'allow',
            'finance:read': 'allow',
            'finance:manage': 'allow',
          },
          users_count: 3,
        },
        {
          id: 'role-pastor',
          nombre: 'PASTOR',
          permisos: {
            'crm:read': 'allow',
            'crm:edit': 'allow',
            'evangelism:read': 'allow',
            'evangelism:manage': 'allow',
          },
          users_count: 5,
        },
        {
          id: 'role-coordinador',
          nombre: 'COORDINADOR',
          permisos: {
            'crm:read': 'allow',
            'academy:read': 'allow',
            'messaging:read': 'allow',
            'messaging:edit': 'allow',
          },
          users_count: 12,
        },
        {
          id: 'role-miembro',
          nombre: 'MIEMBRO',
          permisos: {
            'crm:read': 'allow',
            'messaging:read': 'allow',
          },
          users_count: 150,
        },
      ],
      total: 4,
    }),
  });
}

async function handleAdminUsers(route: Route) {
  const method = route.request().method();

  // POST /admin/users — create user (this path is not matched by the regex for list-only)
  if (method === 'POST') {
    const body = route.request().postDataJSON?.() || {};
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        items: [
          {
            id: `mock-user-${Date.now()}`,
            username: body.username || 'nuevo.usuario',
            email: body.email || 'nuevo@ccf.local',
            role: body.role || 'MIEMBRO',
            is_active: true,
          },
        ],
        total: 1,
      }),
    });
    return;
  }

  // GET /admin/users — list users
  if (method !== 'GET') {
    return route.continue();
  }

  await route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      items: [
        {
          id: 'user-001',
          username: 'admin.central',
          email: 'admin@ccf.com',
          role: 'ADMINISTRADOR',
          is_active: true,
          rol_plataforma_id: 'role-admin',
        },
        {
          id: 'user-002',
          username: 'pastor.juan',
          email: 'juan@ccf.com',
          role: 'PASTOR',
          is_active: true,
          rol_plataforma_id: 'role-pastor',
        },
        {
          id: 'user-003',
          username: 'coord.maria',
          email: 'maria@ccf.com',
          role: 'COORDINADOR',
          is_active: true,
          rol_plataforma_id: 'role-coordinador',
        },
        {
          id: 'user-004',
          username: 'usuario.inactivo',
          email: 'inactivo@ccf.com',
          role: 'MIEMBRO',
          is_active: false,
          rol_plataforma_id: null,
        },
      ],
      total: 4,
    }),
  });
}

async function handleAdminUserPermissions(route: Route) {
  const method = route.request().method();
  const url = route.request().url();
  const userId = url.split('/admin/users/')[1]?.split('/permissions')[0] || 'unknown';

  // PUT /admin/users/:id/permissions — save user overrides
  if (method === 'PUT') {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'ok' }),
    });
    return;
  }

  // GET /admin/users/:id/permissions — load user overrides
  if (method !== 'GET') {
    return route.continue();
  }

  await route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      user_id: userId,
      username: 'usuario.demo',
      email: 'usuario@ccf.local',
      role: 'MIEMBRO',
      role_permissions: { 'crm:read': 'allow', 'messaging:read': 'allow' },
      override_permissions: {},
      module_roles: [],
      effective_permissions: { 'crm:read': 'allow', 'messaging:read': 'allow' },
    }),
  });
}

async function handleWorkspaceConfig(route: Route) {
  if (route.request().method() !== 'GET') {
    return route.continue();
  }
  await route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      id: 'e2e-workspace',
      name: 'E2E Test Workspace',
      modules: ['admin', 'crm', 'academy', 'finance'],
    }),
  });
}

async function handleAdminPermissions(route: Route) {
  if (route.request().method() !== 'GET') {
    return route.continue();
  }
  await route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      permissions: {
        'crm:read': { label: 'CRM Lectura', description: 'Ver información del CRM' },
        'crm:edit': { label: 'CRM Edición', description: 'Editar registros del CRM' },
        'crm:manage': { label: 'CRM Gestión', description: 'Gestión completa del CRM' },
        'admin:read': { label: 'Admin Lectura', description: 'Ver panel de administración' },
        'admin:edit': { label: 'Admin Edición', description: 'Editar configuración' },
        'admin:manage': { label: 'Admin Gestión', description: 'Gestión completa' },
        'academy:read': { label: 'Academia Lectura', description: 'Ver cursos' },
        'academy:edit': { label: 'Academia Edición', description: 'Editar cursos' },
        'academy:manage': { label: 'Academia Gestión', description: 'Gestión completa' },
        'messaging:read': { label: 'Mensajería Lectura', description: 'Leer mensajes' },
        'messaging:edit': { label: 'Mensajería Edición', description: 'Enviar mensajes' },
        'finance:read': { label: 'Finanzas Lectura', description: 'Ver finanzas' },
        'finance:manage': { label: 'Finanzas Gestión', description: 'Gestión financiera' },
      },
      modules: {
        crm: ['read', 'edit', 'manage'],
        academy: ['read', 'study', 'edit', 'manage'],
        projects: ['read', 'edit', 'manage'],
        finance: ['read', 'manage'],
        cms: ['read', 'edit', 'manage'],
        messaging: ['read', 'edit'],
        evangelism: ['read', 'edit', 'manage'],
        community: ['read', 'edit', 'manage'],
        spiritual_life: ['read', 'edit', 'manage'],
        wiki: ['read', 'edit'],
      },
      levels: {
        read: ['read'],
        study: ['read', 'study'],
        edit: ['read', 'edit'],
        manage: ['read', 'edit', 'manage'],
      },
    }),
  });
}
