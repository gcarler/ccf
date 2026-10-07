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
}));

vi.mock('next/navigation', () => ({
  useParams: () => ({ id: layoutMocks.projectId }),
  usePathname: () => layoutMocks.pathname,
}));

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({ token: layoutMocks.token }),
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
    layoutMocks.apiFetch.mockReset();
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
});
