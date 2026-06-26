import { NextResponse } from 'next/server'

type RouteContext = {
  params: Promise<{
    slug?: string[]
  }>
}

const mockUser = {
  id: 42,
  persona_id: 'PER-42',
  username: 'Demo Pastor',
  email: 'demo@ccf.la',
  role: 'admin',
  xp: 1280,
}

const mockPersonas = [
  {
    id: 1,
    first_name: 'Ana',
    last_name: 'García',
    email: 'ana.garcia@ccf.la',
    grupo_id: 7,
    status: 'Activo',
    phone: '+51 999 222 111',
    created_at: '2024-02-11T10:00:00Z',
    church_role: 'Líder de Consolidación',
  },
  {
    id: 2,
    first_name: 'Luis',
    last_name: 'Martínez',
    email: 'luis.martinez@ccf.la',
    grupo_id: 3,
    status: 'Consolidación',
    phone: '+51 999 555 888',
    created_at: '2024-01-20T13:10:00Z',
    church_role: 'Mentor',
  },
  {
    id: 3,
    first_name: 'María',
    last_name: 'Vargas',
    email: 'maria.vargas@ccf.la',
    grupo_id: null,
    status: 'Nuevo',
    phone: '+51 988 111 444',
    created_at: '2024-03-05T16:45:00Z',
    church_role: 'Persona',
  },
]

const mockProjects = [
  {
    id: 101,
    title: 'Campus Norte',
    description: 'Habilitación del nuevo campus híbrido para discipulados presenciales.',
    status: 'Ejecución',
    owner_id: 7,
    created_at: '2024-01-09T08:15:00Z',
    color: '#2563eb',
    tasks: [
      { id: 1, title: 'Plan arquitectónico', status: 'done' },
      { id: 2, title: 'Equipamiento audiovisual', status: 'doing' },
      { id: 3, title: 'Entrenamiento hosts', status: 'todo' },
    ],
  },
  {
    id: 102,
    title: 'App Grupos',
    description: 'Aplicación móvil para reportes semanales y recursos de grupos vida.',
    status: 'Planificación',
    owner_id: 11,
    created_at: '2024-02-01T12:00:00Z',
    color: '#16a34a',
    tasks: [
      { id: 4, title: 'Mapa de experiencia', status: 'done' },
      { id: 5, title: 'MVP Flutter', status: 'doing' },
    ],
  },
  {
    id: 103,
    title: 'Centro de Atención Pastoral',
    description: 'Consolida CRM + mensajería para seguimiento y voluntariado.',
    status: 'Activo',
    owner_id: 2,
    created_at: '2024-02-18T17:30:00Z',
    color: '#f97316',
    tasks: [
      { id: 6, title: 'Integración WhatsApp', status: 'doing' },
      { id: 7, title: 'Tablero IA', status: 'todo' },
      { id: 8, title: 'Journey voluntarios', status: 'todo' },
    ],
  },
]

const mockCourses = [
  {
    id: 1,
    code: 'FND-101',
    title: 'Fundamentos I',
    description: 'Conoce la cultura de la casa, ADN pastoral y tu propósito.',
    modality: 'formal',
    duration_hours: 24,
    is_self_paced: false,
    cohort_name: 'Q1 2024',
    certificate_type: 'Diploma',
  },
  {
    id: 2,
    code: 'LID-204',
    title: 'Liderazgo Multiplicador',
    description: 'Herramientas para multiplicar grupos vida y redes.',
    modality: 'no_formal',
    duration_hours: 12,
    is_self_paced: true,
    cohort_name: null,
    certificate_type: 'Insignia',
  },
  {
    id: 3,
    code: 'TEC-115',
    title: 'Operación Streaming Pro',
    description: 'Checklist para servicios híbridos con métricas en vivo.',
    modality: 'no_formal',
    duration_hours: 8,
    is_self_paced: true,
    cohort_name: null,
    certificate_type: null,
  },
]

const mockEnrollments = [
  {
    id: 5001,
    status: 'active',
    progress_percent: 68,
    approved: false,
    course: {
      id: 1,
      title: 'Fundamentos I',
      modality: 'formal',
      certificate_type: 'Diploma',
    },
  },
  {
    id: 5002,
    status: 'active',
    progress_percent: 92,
    approved: true,
    course: {
      id: 2,
      title: 'Liderazgo Multiplicador',
      modality: 'no_formal',
      certificate_type: 'Insignia',
    },
  },
]

const mockCertificates = [
  {
    id: 9001,
    enrollment_id: 5002,
    certificate_code: 'CCF-LID-204-9001',
    certificate_type: 'Insignia',
    issued_at: '2024-02-25T15:00:00Z',
  },
]

const mockLessons = {
  1: [
    { id: 201, title: 'Visión y ADN', content: 'Conoce nuestra historia y pilares espirituales.', order_index: 1, duration_minutes: 25 },
    { id: 202, title: 'Cultura Faro', content: 'Prácticas clave para discipulado continuo.', order_index: 2, duration_minutes: 30 },
  ],
  2: [
    { id: 301, title: 'Multiplica tu mesa', content: 'Dinámicas para crecer en grupos vida.', order_index: 1, duration_minutes: 20 },
  ],
}

const responseMap = new Map<string, unknown>([
  ['/crm/personas/', mockPersonas],
  ['/projects', mockProjects],
  ['/courses/', mockCourses],
  ['/auth/me', mockUser],
  ['/auth/logout', { status: 'ok' }],
])

function normalizePath(slug?: string[]) {
  const joined = slug && slug.length ? `/${slug.join('/')}` : '/'
  return joined === '//' ? '/' : joined
}

export async function GET(_: Request, { params }: RouteContext) {
  const resolvedParams = await params
  const rawPath = normalizePath(resolvedParams.slug)
  const withSlash = rawPath.endsWith('/') ? rawPath : `${rawPath}/`
  const withoutSlash = rawPath.endsWith('/') ? rawPath.slice(0, -1) || '/' : rawPath

  if (resolvedParams.slug?.[0] === 'users' && resolvedParams.slug[2] === 'enrollments') {
    return NextResponse.json(mockEnrollments)
  }

  if (resolvedParams.slug?.[0] === 'users' && resolvedParams.slug[2] === 'certificates') {
    return NextResponse.json(mockCertificates)
  }

  if (resolvedParams.slug?.[0] === 'courses' && resolvedParams.slug[2] === 'lessons') {
    const courseId = Number(resolvedParams.slug[1])
    return NextResponse.json(mockLessons[courseId as 1 | 2] ?? [])
  }

  const body = responseMap.get(withSlash) ?? responseMap.get(withoutSlash)
  if (!body) {
    return NextResponse.json({ error: 'mock endpoint not found', path: rawPath }, { status: 404 })
  }
  return NextResponse.json(body)
}

export async function POST(request: Request, { params }: RouteContext) {
  const resolvedParams = await params
  const rawPath = normalizePath(resolvedParams.slug)
  if (rawPath.startsWith('/enrollments/') && rawPath.endsWith('/check-in')) {
    return NextResponse.json({ status: 'checked-in' })
  }
  if (rawPath.startsWith('/enrollments/') && rawPath.includes('/assessments/') && rawPath.endsWith('/submit')) {
    return NextResponse.json({ passed: true })
  }
  if (rawPath === '/auth/logout') {
    return NextResponse.json({ status: 'ok' })
  }
  if (rawPath.startsWith('/lessons/') && rawPath.endsWith('/submit-assignment')) {
    await request.blob().catch(() => undefined)
    return NextResponse.json({ status: 'uploaded' })
  }
  return NextResponse.json({ error: 'mock endpoint not found', path: rawPath }, { status: 404 })
}
