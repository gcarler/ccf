import React from 'react';
import { render, act, fireEvent, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import ProjectsClient, { resolveProjectViewParam } from './ProjectsClient';
import { createMockProject } from '@/test-utils/factories';
import { PROJECTS_LIST_ANCHOR } from './projectsLinks';
import type { ProjectRecord } from '@/types/projects';

type MotionDivMockProps = React.HTMLAttributes<HTMLDivElement> & {
  onAnimationComplete?: () => void;
  _initial?: unknown;
  _animate?: unknown;
  _exit?: unknown;
};

type CreateProjectMockInput = {
  title: string;
  description: string;
  status: string;
  owner_id: string | null;
  color: string;
};

const {
  apiFetchMock,
  updateProjectMock,
  deleteProjectMock,
  toastErrorMock,
  routerPushMock,
  routerReplaceMock,
  mockSearchParamsState,
} = vi.hoisted(() => ({
  apiFetchMock: vi.fn(),
  updateProjectMock: vi.fn(),
  deleteProjectMock: vi.fn(),
  toastErrorMock: vi.fn(),
  routerPushMock: vi.fn(),
  routerReplaceMock: vi.fn(),
  mockSearchParamsState: { current: new URLSearchParams() },
}));

// Captura el onAnimationComplete del motion.div para dispararlo en el test
// (reemplaza el flujo real de AnimatePresence mode="wait" + animación de entrada).
let capturedAnimationComplete: (() => void) | null = null;

vi.mock('framer-motion', () => ({
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  motion: {
    div: ({ children, onAnimationComplete, _initial, _animate, _exit, ...props }: MotionDivMockProps) => {
      capturedAnimationComplete = onAnimationComplete ?? null;
      return <div {...props}>{children}</div>;
    },
  },
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: routerPushMock, replace: routerReplaceMock }),
  useSearchParams: () => mockSearchParamsState.current,
}));

vi.mock('next/link', () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => <a href={href}>{children}</a>,
}));

vi.mock('next/dynamic', () => ({
  __esModule: true,
  default: () => {
    const Dummy = () => <div />;
    return Dummy;
  },
}));

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({ token: 'test-token', loading: false }),
}));

vi.mock('@/context/CommandCenterContext', () => ({
  useRegisterCommands: vi.fn(),
}));

vi.mock('@/hooks/useProjects', () => ({
  useProjects: () => ({ updateProject: updateProjectMock, deleteProject: deleteProjectMock }),
}));

vi.mock('@/lib/http', () => ({
  apiFetch: apiFetchMock,
}));

vi.mock('@/design', () => ({
  DSCard: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DSChart: () => <div />,
  DSMetric: () => <div />,
}));

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: toastErrorMock },
}));

vi.mock('@/components/projects/ProjectsShell', () => ({
  default: ({ children, rightActions }: { children: React.ReactNode; rightActions?: React.ReactNode }) => <div>{rightActions}{children}</div>,
}));

vi.mock('@/components/projects/ProjectCreationDrawer', () => ({
  default: ({ isOpen, onSubmit }: { isOpen: boolean; onSubmit: (data: CreateProjectMockInput) => void }) => isOpen
    ? <button type="button" onClick={() => onSubmit({ title: 'Proyecto recién creado', description: '', status: 'planning', owner_id: null, color: '' })}>Guardar proyecto de prueba</button>
    : null,
}));

vi.mock('./views/ProjectsGridView', () => ({
  default: ({ projects, onUpdate, onDelete }: { projects: ProjectRecord[]; onUpdate: (id: string, patch: Partial<ProjectRecord>) => void; onDelete?: (id: string) => void }) => (
    <div>
      <output data-testid="project-order">{projects.map((item) => item.title).join('|')}</output>
      {projects.map((item) => (
        <React.Fragment key={item.id}>
          <button type="button" onClick={() => onUpdate(item.id, { title: 'Título temporal' })}>Actualizar {item.id}</button>
          {onDelete && <button type="button" onClick={() => onDelete(item.id)}>Eliminar {item.id}</button>}
        </React.Fragment>
      ))}
    </div>
  ),
}));
vi.mock('./views/ProjectsListView', () => ({ default: () => <div>list</div> }));
vi.mock('./views/ProjectsTableView', () => ({ default: () => <div>table</div> }));
vi.mock('./views/ProjectsBoardView', () => ({ default: () => <div>board</div> }));

describe('ProjectsClient scroll-to-list (fix carrera 100ms vs ~300ms)', () => {
  const project = createMockProject({ id: 'p1', title: 'Proyecto Alpha', description: 'Desc' });

  beforeEach(() => {
    capturedAnimationComplete = null;
    vi.clearAllMocks();
    mockSearchParamsState.current = new URLSearchParams();
    routerPushMock.mockReset();
    routerReplaceMock.mockReset();
    updateProjectMock.mockResolvedValue(project);
    deleteProjectMock.mockResolvedValue(true);
    apiFetchMock.mockImplementation((path: string) =>
      path === '/projects/summary-page'
        ? Promise.resolve({ items: [], total: 0, skip: 0, limit: 50 })
        : Promise.resolve({ cards: [], workload_distribution: [], delayed_tasks_count: 0 }),
    );
  });

  it('muestra skeleton antes de resolver la carga inicial de proyectos', async () => {
    let resolveProjects: ((page: { items: ProjectRecord[]; total: number; skip: number; limit: number }) => void) | undefined;
    apiFetchMock.mockImplementation((path: string) =>
      path === '/projects/summary-page'
        ? new Promise((resolve) => { resolveProjects = resolve; })
        : Promise.resolve({ cards: [], workload_distribution: [], delayed_tasks_count: 0 }),
    );

    render(<ProjectsClient initialProjects={[]} />);
    expect(screen.getByRole('status', { name: 'Cargando proyectos' })).toBeTruthy();

    await waitFor(() => expect(resolveProjects).toBeTypeOf('function'));
    await act(async () => resolveProjects?.({ items: [], total: 0, skip: 0, limit: 50 }));
    await waitFor(() => expect(screen.getByText('No hay proyectos')).toBeTruthy());
  });

  it('permite reintentar la carga inicial cuando falla', async () => {
    let projectRequests = 0;
    apiFetchMock.mockImplementation((path: string) => {
      if (path !== '/projects/summary-page') {
        return Promise.resolve({ cards: [], workload_distribution: [], delayed_tasks_count: 0 });
      }
      projectRequests += 1;
      return projectRequests === 1
        ? Promise.reject(new Error('offline'))
        : Promise.resolve({ items: [], total: 0, skip: 0, limit: 50 });
    });

    render(<ProjectsClient initialProjects={[]} />);
    const retryButton = await screen.findByRole('button', { name: 'Reintentar' });
    fireEvent.click(retryButton);

    await waitFor(() => expect(screen.getByText('No hay proyectos')).toBeTruthy());
    expect(projectRequests).toBe(2);
  });

  it('paginates the full project collection through the bounded endpoint', async () => {
    const lastProject = createMockProject({ id: 'p51', title: 'Proyecto página dos' });
    apiFetchMock.mockImplementation((path: string, options?: { query?: Record<string, unknown> }) => {
      if (path === '/projects/summary-page') {
        const offset = options?.query?.offset ?? 0;
        return Promise.resolve({
          items: offset === 0 ? [project] : [lastProject],
          total: 51,
          skip: offset,
          limit: 50,
        });
      }
      return Promise.resolve({ cards: [], workload_distribution: [], delayed_tasks_count: 0 });
    });

    render(<ProjectsClient initialProjects={[project]} initialViewType="list" />);
    const next = await screen.findByRole('button', { name: 'Siguiente' });
    expect(screen.getByText('Mostrando 1–1 de 51 proyectos')).toBeTruthy();
    fireEvent.click(next);

    await waitFor(() => expect(apiFetchMock).toHaveBeenCalledWith(
      '/projects/summary-page',
      expect.objectContaining({ query: expect.objectContaining({ offset: 50, limit: 50 }) }),
    ));
    expect(await screen.findByText('Mostrando 51–51 de 51 proyectos')).toBeTruthy();
  });

  it('reconcilia una creación desde el servidor y conserva los filtros activos', async () => {
    const createdProject = createMockProject({ id: 'new-project', title: 'Proyecto recién creado' });
    apiFetchMock.mockImplementation((path: string) => {
      if (path === '/projects/summary-page') {
        return Promise.resolve({ items: [project], total: 12, skip: 0, limit: 50 });
      }
      if (path === '/projects') return Promise.resolve(createdProject);
      return Promise.resolve({ cards: [], workload_distribution: [], delayed_tasks_count: 0 });
    });

    render(<ProjectsClient initialProjects={[project]} initialViewType="list" />);
    await act(async () => {});
    fireEvent.change(screen.getByPlaceholderText('Buscar proyectos'), { target: { value: 'Alpha' } });
    await waitFor(() => expect(apiFetchMock).toHaveBeenCalledWith(
      '/projects/summary-page',
      expect.objectContaining({ query: expect.objectContaining({ search: 'Alpha', offset: 0 }) }),
    ));

    fireEvent.click(screen.getByRole('button', { name: 'Nuevo Proyecto' }));
    fireEvent.click(screen.getByRole('button', { name: 'Guardar proyecto de prueba' }));

    await waitFor(() => expect(apiFetchMock.mock.calls.filter(([path]) => path === '/projects/summary-page')).toHaveLength(2));
    expect(apiFetchMock.mock.calls.filter(([path]) => path === '/projects/summary-page').at(-1)?.[1]).toEqual(
      expect.objectContaining({ query: expect.objectContaining({ search: 'Alpha', offset: 0 }) }),
    );
  });

  it('informa y revierte una actualización rechazada por la API', async () => {
    updateProjectMock.mockResolvedValue(null);
    apiFetchMock.mockImplementation((path: string) => path === '/projects/summary-page'
      ? Promise.resolve({ items: [project], total: 1, skip: 0, limit: 50 })
      : Promise.resolve({ cards: [], workload_distribution: [], delayed_tasks_count: 0 }));
    render(<ProjectsClient initialProjects={[project]} initialViewType="grid" />);
    await screen.findByTestId('project-order');

    fireEvent.click(screen.getByRole('button', { name: 'Actualizar p1' }));

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('No se pudo actualizar el proyecto. Se conservaron los datos guardados.'));
    expect(screen.getByTestId('project-order')).toHaveTextContent('Proyecto Alpha');
  });

  it('restaura la posición original y notifica si falla el borrado', async () => {
    deleteProjectMock.mockResolvedValue(false);
    const secondProject = createMockProject({ id: 'p2', title: 'Proyecto Beta' });
    const thirdProject = createMockProject({ id: 'p3', title: 'Proyecto Gamma' });
    apiFetchMock.mockImplementation((path: string) => path === '/projects/summary-page'
      ? Promise.resolve({ items: [project, secondProject, thirdProject], total: 3, skip: 0, limit: 50 })
      : Promise.resolve({ cards: [], workload_distribution: [], delayed_tasks_count: 0 }));
    render(<ProjectsClient initialProjects={[project, secondProject, thirdProject]} initialViewType="grid" />);
    await screen.findByTestId('project-order');

    fireEvent.click(screen.getByRole('button', { name: 'Eliminar p2' }));

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('No se pudo eliminar el proyecto. La lista se sincronizó con el servidor.'));
    expect(screen.getByTestId('project-order')).toHaveTextContent('Proyecto Alpha|Proyecto Beta|Proyecto Gamma');
  });

  it('no restaura una eliminación fallida dentro de otra búsqueda', async () => {
    let finishDelete: ((success: boolean) => void) | undefined;
    deleteProjectMock.mockReturnValue(new Promise((resolve) => { finishDelete = resolve; }));
    const betaProject = createMockProject({ id: 'p2', title: 'Proyecto Beta' });
    apiFetchMock.mockImplementation((path: string, options?: { query?: Record<string, unknown> }) => {
      if (path === '/projects/summary-page') {
        const isBetaSearch = options?.query?.search === 'Beta';
        const items = isBetaSearch ? [betaProject] : [project];
        return Promise.resolve({ items, total: items.length, skip: 0, limit: 50 });
      }
      return Promise.resolve({ cards: [], workload_distribution: [], delayed_tasks_count: 0 });
    });
    render(<ProjectsClient initialProjects={[project]} initialViewType="grid" />);
    await screen.findByTestId('project-order');

    fireEvent.click(screen.getByRole('button', { name: 'Eliminar p1' }));
    fireEvent.change(screen.getByPlaceholderText('Buscar proyectos'), { target: { value: 'Beta' } });
    await waitFor(() => expect(screen.getByTestId('project-order')).toHaveTextContent('Proyecto Beta'));

    await act(async () => { finishDelete?.(false); });

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('No se pudo eliminar el proyecto. La lista se sincronizó con el servidor.'));
    await waitFor(() => expect(apiFetchMock.mock.calls.filter(([path, options]) =>
      path === '/projects/summary-page' && options?.query?.search === 'Beta',
    ).length).toBeGreaterThanOrEqual(2));
    expect(screen.getByTestId('project-order')).toHaveTextContent('Proyecto Beta');
    expect(screen.queryByText('Proyecto Alpha')).toBeNull();
  });

  it('reserva métricas y gráficos para Resumen, sin desplazar Calendario', async () => {
    const { unmount } = render(<ProjectsClient initialProjects={[project]} initialViewType="dashboard" />);
    await act(async () => {});
    expect(screen.getByTestId('projects-overview')).toBeTruthy();

    unmount();
    render(<ProjectsClient initialProjects={[project]} initialViewType="calendar" />);
    expect(screen.queryByTestId('projects-overview')).toBeNull();
  });

  it('carga métricas solo cuando se selecciona Resumen', async () => {
    let dashboardRequests = 0;
    apiFetchMock.mockImplementation((path: string) => {
      if (path === '/dashboard/projects') dashboardRequests += 1;
      return Promise.resolve(path === '/projects/summary-page' ? { items: [project], total: 1, skip: 0, limit: 50 } : { cards: [], workload_distribution: [], delayed_tasks_count: 0 });
    });

    render(<ProjectsClient initialProjects={[project]} initialViewType="calendar" />);
    await act(async () => {});
    expect(dashboardRequests).toBe(0);

    fireEvent.change(screen.getByRole('combobox', { name: 'Vista de proyectos' }), { target: { value: 'dashboard' } });
    await waitFor(() => expect(dashboardRequests).toBe(1));
  });

  it('permite reintentar las métricas del resumen después de un error', async () => {
    let dashboardRequests = 0;
    apiFetchMock.mockImplementation((path: string) => {
      if (path === '/dashboard/projects') {
        dashboardRequests += 1;
        return dashboardRequests === 1
          ? Promise.reject(new Error('offline'))
          : Promise.resolve({ cards: [{ title: 'Proyectos activos', value: '3' }], workload_distribution: [], delayed_tasks_count: 0 });
      }
      return Promise.resolve({ items: [project], total: 1, skip: 0, limit: 50 });
    });

    render(<ProjectsClient initialProjects={[project]} initialViewType="dashboard" />);
    fireEvent.click(await screen.findByRole('button', { name: 'Reintentar métricas' }));

    await waitFor(() => expect(screen.queryByRole('alert')).toBeNull());
    expect(dashboardRequests).toBe(2);
  });

  it('expone controles móviles accesibles para cambiar vista y buscar', async () => {
    apiFetchMock.mockImplementation((path: string, options?: { query?: Record<string, unknown> }) =>
      path === '/projects/summary-page'
        ? Promise.resolve(options?.query?.search === 'No existe'
          ? { items: [], total: 0, skip: 0, limit: 50 }
          : { items: [project], total: 1, skip: 0, limit: 50 })
        : Promise.resolve({ cards: [], workload_distribution: [], delayed_tasks_count: 0 }),
    );
    render(<ProjectsClient initialProjects={[project]} initialViewType="list" />);
    await act(async () => {});

    const viewSelect = screen.getByRole('combobox', { name: 'Vista de proyectos' });
    fireEvent.change(viewSelect, { target: { value: 'calendar' } });
    expect(viewSelect).toHaveValue('calendar');

    fireEvent.change(screen.getByPlaceholderText('Buscar proyectos'), { target: { value: 'No existe' } });
    expect(await screen.findByText('Ningún proyecto coincide con tu búsqueda.')).toBeTruthy();
    expect(apiFetchMock).toHaveBeenCalledWith(
      '/projects/summary-page',
      expect.objectContaining({ query: expect.objectContaining({ search: 'No existe', offset: 0 }) }),
    );
  });

  it('dispara scrollIntoView cuando viewType=list y el anchor está montado', async () => {
    const scrollSpy = vi.spyOn(HTMLElement.prototype, 'scrollIntoView').mockImplementation(() => {});
    try {
      const { container } = render(
        <ProjectsClient initialProjects={[project]} initialViewType="list" />,
      );
      // Flush del useEffect del dashboard (apiFetch async) para evitar
      // warnings de act() con el setState fuera de act.
      await act(async () => {});

      // El wrapper del listado con el id del anchor debe existir en el DOM.
      expect(container.querySelector(`#${PROJECTS_LIST_ANCHOR}`)).toBeTruthy();
      expect(capturedAnimationComplete).toBeTruthy();

      // Simula la finalización de la animación de entrada (el momento en que
      // AnimatePresence mode="wait" ya montó la vista y el ref está poblado).
      act(() => {
        capturedAnimationComplete?.();
      });

      expect(scrollSpy).toHaveBeenCalledWith({ behavior: 'smooth', block: 'start' });
    } finally {
      scrollSpy.mockRestore();
    }
  });

  it('no dispara scrollIntoView en vista grid (guard viewType !== list)', async () => {
    const scrollSpy = vi.spyOn(HTMLElement.prototype, 'scrollIntoView').mockImplementation(() => {});
    try {
      render(<ProjectsClient initialProjects={[project]} initialViewType="grid" />);
      await act(async () => {});

      expect(capturedAnimationComplete).toBeTruthy();
      act(() => {
        capturedAnimationComplete?.();
      });

      expect(scrollSpy).not.toHaveBeenCalled();
    } finally {
      scrollSpy.mockRestore();
    }
  });

  it('scrollea solo una vez por transición a la vista list (guard scrollTriggeredViewRef)', async () => {
    const scrollSpy = vi.spyOn(HTMLElement.prototype, 'scrollIntoView').mockImplementation(() => {});
    try {
      render(<ProjectsClient initialProjects={[project]} initialViewType="list" />);
      await act(async () => {});

      act(() => {
        capturedAnimationComplete?.();
      });
      act(() => {
        capturedAnimationComplete?.();
      });

      expect(scrollSpy).toHaveBeenCalledTimes(1);
    } finally {
      scrollSpy.mockRestore();
    }
  });

  it('scrollea al anchor incluso cuando filtered está vacío (FIX-06a monta anchor en empty state)', async () => {
    const scrollSpy = vi.spyOn(HTMLElement.prototype, 'scrollIntoView').mockImplementation(() => {});
    try {
      // FIX-06a: cuando viewType==='list' y filtered está vacío, el anchor
      // #projects-dashboard se monta dentro del div con ref para que el hash
      // scroll siga funcionando. El ref ya NO es null → el scroll se ejecuta.
      render(<ProjectsClient initialProjects={[]} initialViewType="list" />);
      await screen.findByText('No hay proyectos');

      act(() => {
        capturedAnimationComplete?.();
      });

      expect(scrollSpy).toHaveBeenCalled();
    } finally {
      scrollSpy.mockRestore();
    }
  });
});

describe('resolveProjectViewParam helper', () => {
  it('resuelve correctamente todas las vistas canónicas válidas', () => {
    const validViews = ['dashboard', 'grid', 'table', 'list', 'board', 'kanban', 'calendar', 'gantt', 'wiki'] as const;
    validViews.forEach((view) => {
      expect(resolveProjectViewParam(view)).toBe(view);
    });
  });

  it('normaliza el prefijo dashboar y variantes a dashboard', () => {
    expect(resolveProjectViewParam('dashboar')).toBe('dashboard');
    expect(resolveProjectViewParam('  dashboar  ')).toBe('dashboard');
    expect(resolveProjectViewParam('Dashboar')).toBe('dashboard');
    expect(resolveProjectViewParam('DASHBOARD')).toBe('dashboard');
  });

  it('normaliza vistas válidas con espacios o mayúsculas', () => {
    expect(resolveProjectViewParam('  LiSt ')).toBe('list');
    expect(resolveProjectViewParam('TABLE')).toBe('table');
  });

  it('retorna el fallback especificado cuando el valor es nulo, vacío o desconocido', () => {
    expect(resolveProjectViewParam(null, 'grid')).toBe('grid');
    expect(resolveProjectViewParam(undefined, 'table')).toBe('table');
    expect(resolveProjectViewParam('', 'board')).toBe('board');
    expect(resolveProjectViewParam('unknown_view', 'list')).toBe('list');
    expect(resolveProjectViewParam(null)).toBe('dashboard');
  });
});

describe('ProjectsClient view URL conflict & synchronization', () => {
  const project = createMockProject({ id: 'p1', title: 'Proyecto Alpha', description: 'Desc' });

  beforeEach(() => {
    capturedAnimationComplete = null;
    vi.clearAllMocks();
    mockSearchParamsState.current = new URLSearchParams();
    routerPushMock.mockReset();
    routerReplaceMock.mockReset();
    updateProjectMock.mockResolvedValue(project);
    deleteProjectMock.mockResolvedValue(true);
    apiFetchMock.mockImplementation((path: string) =>
      path === '/projects/summary-page'
        ? Promise.resolve({ items: [project], total: 1, skip: 0, limit: 50 })
        : Promise.resolve({ cards: [], workload_distribution: [], delayed_tasks_count: 0 }),
    );
  });

  it('montaje con initialViewType=dashboard y searchParams view=list no reemplaza a dashboard ni consulta /dashboard/projects', async () => {
    mockSearchParamsState.current = new URLSearchParams('view=list');
    render(<ProjectsClient initialProjects={[project]} initialViewType="dashboard" />);
    await act(async () => {});

    // No debe consultar /dashboard/projects porque la vista inicial es 'list'
    expect(apiFetchMock).not.toHaveBeenCalledWith('/dashboard/projects', expect.anything());

    // No debe haber conflicto ni sobreescritura a view=dashboard en router.replace
    expect(routerReplaceMock).not.toHaveBeenCalledWith(expect.stringContaining('view=dashboard'), expect.anything());

    // El selector móvil refleja la vista 'list'
    const viewSelect = screen.getByRole('combobox', { name: 'Vista de proyectos' });
    expect(viewSelect).toHaveValue('list');
  });

  it('sincroniza el cambio externo de searchParams de dashboard a list sin revertir la URL', async () => {
    mockSearchParamsState.current = new URLSearchParams('view=dashboard');
    const { rerender } = render(<ProjectsClient initialProjects={[project]} initialViewType="dashboard" />);
    await act(async () => {});

    routerReplaceMock.mockClear();

    // Simular que Next.js actualiza searchParams externamente a ?view=list
    mockSearchParamsState.current = new URLSearchParams('view=list');
    rerender(<ProjectsClient initialProjects={[project]} initialViewType="dashboard" />);
    await act(async () => {});

    // La vista se sincroniza a 'list'
    const viewSelect = screen.getByRole('combobox', { name: 'Vista de proyectos' });
    expect(viewSelect).toHaveValue('list');

    // No debe revertir la URL con router.replace a view=dashboard
    expect(routerReplaceMock).not.toHaveBeenCalledWith(expect.stringContaining('view=dashboard'), expect.anything());
  });

  it('normaliza view=dashboar a view=dashboard en el montaje inicial', async () => {
    mockSearchParamsState.current = new URLSearchParams('view=dashboar');
    render(<ProjectsClient initialProjects={[project]} initialViewType="list" />);
    await act(async () => {});

    // La vista resuelta es dashboard
    const viewSelect = screen.getByRole('combobox', { name: 'Vista de proyectos' });
    expect(viewSelect).toHaveValue('dashboard');

    // router.replace debe invocarse normalizando a view=dashboard
    expect(routerReplaceMock).toHaveBeenCalledWith(
      '/plataforma/projects?view=dashboard',
      expect.objectContaining({ scroll: false }),
    );
    expect(routerReplaceMock).not.toHaveBeenCalledWith(
      expect.stringMatching(/[?&]view=dashboar(?:&|$)/),
      expect.anything(),
    );
  });

  it('actualiza router.replace cuando el usuario cambia la vista desde la interfaz', async () => {
    mockSearchParamsState.current = new URLSearchParams('view=dashboard');
    render(<ProjectsClient initialProjects={[project]} initialViewType="dashboard" />);
    await act(async () => {});

    routerReplaceMock.mockClear();

    const viewSelect = screen.getByRole('combobox', { name: 'Vista de proyectos' });
    fireEvent.change(viewSelect, { target: { value: 'board' } });

    expect(viewSelect).toHaveValue('board');
    expect(routerReplaceMock).toHaveBeenCalledWith(
      expect.stringContaining('view=board'),
      expect.objectContaining({ scroll: false }),
    );
  });

  it('actualiza router.replace cuando el usuario cambia el filtro de estado desde la interfaz', async () => {
    mockSearchParamsState.current = new URLSearchParams('view=grid');
    render(<ProjectsClient initialProjects={[project]} initialViewType="grid" />);
    await act(async () => {});

    routerReplaceMock.mockClear();

    const activeFilterButton = screen.getByRole('button', { name: 'Activo' });
    fireEvent.click(activeFilterButton);

    expect(routerReplaceMock).toHaveBeenCalledWith(
      expect.stringContaining('status=active'),
      expect.objectContaining({ scroll: false }),
    );
  });
});

