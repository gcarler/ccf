import React from 'react';
import { act, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ProjectsLayoutClient from './ProjectsLayoutClient';
import type { ProjectRecord, ProjectSummaryPageResponse } from '@/types/projects';

const layoutMocks = vi.hoisted(() => ({
  projectId: 'project-a' as string | undefined,
  pathname: '/plataforma/projects/project-a',
  token: 'test-token',
  apiFetch: vi.fn(),
  openLayer: vi.fn(),
  resetSidebarStack: vi.fn(),
  layers: { S1: true, S2: true, S3: false },
}));

vi.mock('next/navigation', () => ({
  useParams: () => ({ id: layoutMocks.projectId }),
  usePathname: () => layoutMocks.pathname,
}));

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({ token: layoutMocks.token }),
}));

vi.mock('@/context/SidebarLayerContext', () => ({
  useSidebarLayers: () => ({
    layers: layoutMocks.layers,
    openLayer: layoutMocks.openLayer,
    closeLayer: vi.fn(),
    resetSidebarStack: layoutMocks.resetSidebarStack,
  }),
}));

vi.mock('@/lib/http', () => ({
  apiFetch: layoutMocks.apiFetch,
}));

vi.mock('@/components/WorkspaceLayout', () => ({
  default: ({ children, sidebarSections }: {
    children: React.ReactNode;
    sidebarSections: Array<{ title: string; items: Array<{ id: string; label: string; href: string }> }>;
  }) => (
    <div>
      {sidebarSections.map((section) => <h2 key={section.title}>{section.title}</h2>)}
      <nav aria-label="Navegación del proyecto">
        {sidebarSections.flatMap((section) => section.items).map((item) => (
          <a key={item.id} href={item.href}>{item.label}</a>
        ))}
      </nav>
      {children}
    </div>
  ),
}));

vi.mock('@/components/ModuleErrorBoundary', () => ({
  ModuleErrorBoundary: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock('sonner', () => ({
  toast: { error: vi.fn() },
}));

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
}

function projectRecord(id: string, title: string, taskId: string, taskTitle: string): ProjectRecord {
  return {
    id,
    title,
    status: 'active',
    color: null,
    description: '',
    tasks: [{ id: taskId, title: taskTitle, status: 'todo' }],
  } as ProjectRecord;
}

describe('ProjectsLayoutClient', () => {
  beforeEach(() => {
    layoutMocks.projectId = 'project-a';
    layoutMocks.pathname = '/plataforma/projects/project-a';
    layoutMocks.token = 'test-token';
    layoutMocks.layers = { S1: true, S2: true, S3: false };
    layoutMocks.openLayer.mockClear();
    layoutMocks.resetSidebarStack.mockClear();
    layoutMocks.apiFetch.mockReset();
    localStorage.clear();
  });

  it('clears the previous project navigation and ignores stale responses after a project switch', async () => {
    const projectA = deferred<ProjectRecord>();
    const projectB = deferred<ProjectRecord>();
    const projectC = deferred<ProjectRecord>();
    layoutMocks.apiFetch
      .mockReturnValueOnce(projectA.promise)
      .mockReturnValueOnce(projectB.promise)
      .mockReturnValueOnce(projectC.promise);

    const { rerender } = render(
      <ProjectsLayoutClient initialProjectPage={null}><main>Contenido</main></ProjectsLayoutClient>,
    );

    await waitFor(() => expect(layoutMocks.apiFetch).toHaveBeenCalledWith('/projects/project-a', expect.objectContaining({ token: 'test-token', signal: expect.any(AbortSignal) })));
    await act(async () => {
      projectA.resolve(projectRecord('project-a', 'Proyecto A', 'task-a', 'Tarea exclusiva A'));
      await projectA.promise;
    });
    expect(screen.getByRole('link', { name: 'Tarea exclusiva A' })).toHaveAttribute('href', '/plataforma/projects/project-a?task=task-a');

    layoutMocks.projectId = 'project-b';
    layoutMocks.pathname = '/plataforma/projects/project-b';
    rerender(<ProjectsLayoutClient initialProjectPage={null}><main>Contenido</main></ProjectsLayoutClient>);

    await waitFor(() => expect(layoutMocks.apiFetch).toHaveBeenCalledWith('/projects/project-b', expect.objectContaining({ token: 'test-token', signal: expect.any(AbortSignal) })));
    expect(screen.queryByRole('link', { name: 'Tarea exclusiva A' })).not.toBeInTheDocument();

    layoutMocks.projectId = 'project-c';
    layoutMocks.pathname = '/plataforma/projects/project-c';
    rerender(<ProjectsLayoutClient initialProjectPage={null}><main>Contenido</main></ProjectsLayoutClient>);
    await waitFor(() => expect(layoutMocks.apiFetch).toHaveBeenCalledWith('/projects/project-c', expect.objectContaining({ token: 'test-token', signal: expect.any(AbortSignal) })));

    await act(async () => {
      projectC.resolve(projectRecord('project-c', 'Proyecto C', 'task-c', 'Tarea exclusiva C'));
      await projectC.promise;
    });
    await act(async () => {
      projectB.resolve(projectRecord('project-b', 'Proyecto B', 'task-b', 'Tarea exclusiva B'));
      await projectB.promise;
    });

    expect(screen.getByRole('link', { name: 'Tarea exclusiva C' })).toHaveAttribute('href', '/plataforma/projects/project-c?task=task-c');
    expect(screen.queryByRole('link', { name: 'Tarea exclusiva B' })).not.toBeInTheDocument();
  });

  it('loads the global sidebar from the bounded summary endpoint', async () => {
    layoutMocks.projectId = undefined;
    layoutMocks.pathname = '/plataforma/projects';
    layoutMocks.apiFetch.mockResolvedValue({
      items: [{ id: 'project-1', title: 'Proyecto visible' }],
      total: 1,
      skip: 0,
      limit: 50,
    });

    render(<ProjectsLayoutClient initialProjectPage={null}><main>Contenido</main></ProjectsLayoutClient>);

    expect(await screen.findByRole('link', { name: 'Proyecto visible' })).toHaveAttribute(
      'href',
      '/plataforma/projects/project-1?view=list',
    );
    expect(layoutMocks.apiFetch).toHaveBeenCalledWith('/projects/summary-page', {
      token: 'test-token',
      cache: undefined,
      signal: expect.any(AbortSignal),
      query: { offset: 0, limit: 100 },
    });
  });

  it('reuses the SSR first page and loads every remaining page with a neutral section title', async () => {
    const initialItems = Array.from({ length: 100 }, (_, index) => ({
      id: `project-${index + 1}`,
      title: `Proyecto ${index + 1}`,
    })) as ProjectSummaryPageResponse['items'];
    const lastProject = { id: 'project-101', title: 'Proyecto 101' };
    layoutMocks.projectId = undefined;
    layoutMocks.pathname = '/plataforma/projects';
    layoutMocks.apiFetch.mockResolvedValueOnce({
      items: [lastProject],
      total: 101,
      skip: 100,
      limit: 100,
    });

    render(
      <ProjectsLayoutClient
        initialProjectPage={{ items: initialItems, total: 101, skip: 0, limit: 100 } as ProjectSummaryPageResponse}
      >
        <main>Contenido</main>
      </ProjectsLayoutClient>,
    );

    expect(await screen.findByRole('link', { name: 'Proyecto 101' })).toHaveAttribute(
      'href',
      '/plataforma/projects/project-101?view=list',
    );
    expect(screen.getByRole('heading', { name: 'Proyectos' })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Proyectos Activos' })).not.toBeInTheDocument();
    expect(layoutMocks.apiFetch).toHaveBeenCalledTimes(1);
    expect(layoutMocks.apiFetch).toHaveBeenCalledWith('/projects/summary-page', {
      token: 'test-token',
      signal: expect.any(AbortSignal),
      query: { offset: 100, limit: 100 },
    });
  });

  it('preserves current project sidebar without resetting to null on project-updated event for same project', async () => {
    const projectA = deferred<ProjectRecord>();
    layoutMocks.apiFetch.mockReturnValueOnce(projectA.promise);

    render(
      <ProjectsLayoutClient initialProjectPage={null}><main>Contenido</main></ProjectsLayoutClient>,
    );

    await act(async () => {
      projectA.resolve(projectRecord('project-a', 'Proyecto A', 'task-a', 'Tarea persistente A'));
      await projectA.promise;
    });

    expect(screen.getByRole('link', { name: 'Tarea persistente A' })).toBeInTheDocument();

    // Trigger project-updated event for project-a
    const updateDeferred = deferred<ProjectRecord>();
    layoutMocks.apiFetch.mockReturnValueOnce(updateDeferred.promise);

    await act(async () => {
      window.dispatchEvent(new CustomEvent('project-updated', { detail: { projectId: 'project-a' } }));
    });

    // During the in-flight revalidation, the current project's task link MUST stay in the document (not wiped to null)
    expect(screen.getByRole('link', { name: 'Tarea persistente A' })).toBeInTheDocument();

    await act(async () => {
      updateDeferred.resolve(projectRecord('project-a', 'Proyecto A', 'task-a', 'Tarea persistente A (actualizada)'));
      await updateDeferred.promise;
    });

    expect(screen.getByRole('link', { name: 'Tarea persistente A (actualizada)' })).toBeInTheDocument();
  });

  it('opens S1 and S2 for root and project routes, but respects a manual close on the same route', async () => {
    layoutMocks.apiFetch.mockResolvedValue({ items: [], total: 0, skip: 0, limit: 100 });
    layoutMocks.projectId = undefined;
    layoutMocks.pathname = '/plataforma/projects';
    layoutMocks.layers = { S1: false, S2: false, S3: false };
    const { rerender } = render(
      <ProjectsLayoutClient initialProjectPage={null}><main>Contenido</main></ProjectsLayoutClient>,
    );

    expect(layoutMocks.openLayer).toHaveBeenCalledWith('S1');
    expect(layoutMocks.openLayer).toHaveBeenCalledWith('S2');
    expect(localStorage.getItem('workspace:s2:projects')).toBe('visible');

    layoutMocks.openLayer.mockClear();
    layoutMocks.layers = { S1: true, S2: false, S3: false };
    localStorage.setItem('workspace:s2:projects', 'hidden');
    rerender(<ProjectsLayoutClient initialProjectPage={null}><main>Contenido</main></ProjectsLayoutClient>);
    expect(layoutMocks.openLayer).not.toHaveBeenCalled();
    expect(localStorage.getItem('workspace:s2:projects')).toBe('hidden');

    layoutMocks.projectId = 'project-a';
    layoutMocks.pathname = '/plataforma/projects/project-a';
    rerender(<ProjectsLayoutClient initialProjectPage={null}><main>Contenido</main></ProjectsLayoutClient>);
    expect(layoutMocks.openLayer).toHaveBeenCalledWith('S1');
    expect(layoutMocks.openLayer).toHaveBeenCalledWith('S2');
    expect(localStorage.getItem('workspace:s2:projects')).toBe('visible');

    layoutMocks.openLayer.mockClear();
    layoutMocks.projectId = undefined;
    layoutMocks.pathname = '/plataforma/projects';
    rerender(<ProjectsLayoutClient initialProjectPage={null}><main>Contenido</main></ProjectsLayoutClient>);
    expect(layoutMocks.openLayer).toHaveBeenCalledWith('S1');
    expect(layoutMocks.openLayer).toHaveBeenCalledWith('S2');
  });

  it('reopens both sidebars and resets the drill-down stack for each Projects pathname', () => {
    layoutMocks.projectId = undefined;
    layoutMocks.pathname = '/plataforma/projects/tasks';
    layoutMocks.layers = { S1: false, S2: false, S3: false };
    localStorage.setItem('s2Width', '64');
    const { rerender } = render(
      <ProjectsLayoutClient initialProjectPage={null}><main>Contenido</main></ProjectsLayoutClient>,
    );

    expect(layoutMocks.resetSidebarStack).toHaveBeenCalledTimes(1);
    expect(layoutMocks.openLayer).toHaveBeenCalledWith('S1');
    expect(layoutMocks.openLayer).toHaveBeenCalledWith('S2');
    expect(localStorage.getItem('s2Width')).toBe('280');

    layoutMocks.resetSidebarStack.mockClear();
    layoutMocks.openLayer.mockClear();
    layoutMocks.layers = { S1: true, S2: false, S3: false };
    rerender(<ProjectsLayoutClient initialProjectPage={null}><main>Contenido</main></ProjectsLayoutClient>);
    expect(layoutMocks.resetSidebarStack).not.toHaveBeenCalled();
    expect(layoutMocks.openLayer).not.toHaveBeenCalled();

    layoutMocks.pathname = '/plataforma/projects';
    rerender(<ProjectsLayoutClient initialProjectPage={null}><main>Contenido</main></ProjectsLayoutClient>);
    expect(layoutMocks.resetSidebarStack).toHaveBeenCalledTimes(1);
    expect(layoutMocks.openLayer).toHaveBeenCalledWith('S1');
    expect(layoutMocks.openLayer).toHaveBeenCalledWith('S2');

    layoutMocks.resetSidebarStack.mockClear();
    layoutMocks.openLayer.mockClear();
    layoutMocks.apiFetch.mockResolvedValue(projectRecord('project-a', 'Proyecto A', 'task-a', 'Tarea A'));
    layoutMocks.projectId = 'project-a';
    layoutMocks.pathname = '/plataforma/projects/project-a';
    rerender(<ProjectsLayoutClient initialProjectPage={null}><main>Contenido</main></ProjectsLayoutClient>);
    expect(layoutMocks.resetSidebarStack).toHaveBeenCalledTimes(1);
    expect(layoutMocks.openLayer).toHaveBeenCalledWith('S1');
    expect(layoutMocks.openLayer).toHaveBeenCalledWith('S2');
    expect(localStorage.getItem('workspace:s2:projects')).toBe('visible');
    expect(localStorage.getItem('workspace:focus:projects')).toBe('0');
  });

  it('includes Gobernanza PMI section with IDP/EVM indicators and WBS links when a project is active', async () => {
    layoutMocks.projectId = 'project-a';
    layoutMocks.pathname = '/plataforma/projects/project-a';
    layoutMocks.apiFetch.mockResolvedValueOnce(
      projectRecord('project-a', 'Proyecto A', 'task-a', 'Tarea A'),
    );

    render(
      <ProjectsLayoutClient initialProjectPage={null}>
        <main>Contenido</main>
      </ProjectsLayoutClient>,
    );

    expect(await screen.findByRole('heading', { name: 'Gobernanza PMI' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Indicadores IDP y EVM' })).toHaveAttribute(
      'href',
      '/plataforma/projects/project-a/indicators',
    );
    expect(screen.getByRole('link', { name: 'Estructura WBS / Lista' })).toHaveAttribute(
      'href',
      '/plataforma/projects/project-a?view=list',
    );
  });
});
