import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { ProjectRecord } from '@/types/projects';

const { fetchProjectsMock } = vi.hoisted(() => ({
  fetchProjectsMock: vi.fn(),
}));

vi.mock('./projectsData', () => ({
  fetchProjects: fetchProjectsMock,
}));

vi.mock('./ProjectsClient', () => ({
  default: ({ initialProjects, initialViewType }: { initialProjects: ProjectRecord[]; initialViewType: string }) => (
    <section data-testid="projects-client-mock" data-view={initialViewType}>
      {initialProjects.map((project) => (
        <span key={project.id}>{project.title}</span>
      ))}
    </section>
  ),
}));

import ProjectsPage, { metadata, dynamic } from './page';

describe('ProjectsPage — entrada SSR del portafolio', () => {
  beforeEach(() => {
    fetchProjectsMock.mockReset();
  });

  it('declara los metadatos y el modo de render dinámico', () => {
    expect(metadata.title).toBe('Proyectos · CCF Mesh');
    expect(dynamic).toBe('force-dynamic');
  });

  it('invoca fetchProjects() y renderiza ProjectsClient con initialProjects y vista dashboard', async () => {
    const projects = [
      { id: 'p1', title: 'Proyecto Alpha', status: 'active', created_at: '2026-01-01T00:00:00Z' },
      { id: 'p2', title: 'Proyecto Beta', status: 'planning', created_at: '2026-01-02T00:00:00Z' },
    ] as ProjectRecord[];
    fetchProjectsMock.mockResolvedValueOnce(projects);

    render(await ProjectsPage());

    expect(fetchProjectsMock).toHaveBeenCalledTimes(1);
    const client = screen.getByTestId('projects-client-mock');
    expect(client).toHaveAttribute('data-view', 'dashboard');
    expect(screen.getByText('Proyecto Alpha')).toBeInTheDocument();
    expect(screen.getByText('Proyecto Beta')).toBeInTheDocument();
  });

  it('entrega un array vacío a ProjectsClient cuando el portafolio está vacío', async () => {
    fetchProjectsMock.mockResolvedValueOnce([]);

    render(await ProjectsPage());

    expect(fetchProjectsMock).toHaveBeenCalledTimes(1);
    expect(screen.getByTestId('projects-client-mock').children).toHaveLength(0);
  });
});
