import { fireEvent, render, screen } from '@testing-library/react';
import type { AnchorHTMLAttributes, ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { ProjectRecord } from '@/types/projects';
import { DEFAULT_PROJECT_COLOR } from '@/lib/projects/palette';
import ProjectCard from './ProjectCard';

const authState = vi.hoisted(() => ({
  permissions: {} as Record<string, boolean>,
}));

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({
    user: { role: 'Gestor' },
    hasPermission: (permission: string) =>
      authState.permissions[permission] === true,
  }),
}));

vi.mock('next/link', () => ({
  default: ({ href, children, ...props }: AnchorHTMLAttributes<HTMLAnchorElement> & { href: string; children: ReactNode }) => (
    <a href={href} {...props}>{children}</a>
  ),
}));

vi.mock('@/components/ui/inline-editors/InlineTextInput', () => ({
  InlineTextInput: () => <span />,
}));
vi.mock('@/components/ui/inline-editors/InlineProjectStatusPicker', () => ({
  InlineProjectStatusPicker: () => <span />,
}));
vi.mock('@/components/ui/inline-editors/InlineUserPicker', () => ({
  InlineUserPicker: () => <span />,
}));

const project: ProjectRecord = {
  id: 'project-1',
  title: 'Plan anual',
  status: 'planning',
  created_at: '2026-10-01T10:00:00Z',
};

describe('ProjectCard delete capability', () => {
  beforeEach(() => {
    authState.permissions = {};
  });

  it('shows delete to a Gestor authorized by the backend policy', () => {
    authState.permissions['projects:manage'] = true;
    authState.permissions['academy:manage'] = true;
    const onDelete = vi.fn();

    render(<ProjectCard project={project} index={0} onDelete={onDelete} />);
    fireEvent.click(screen.getByRole('button', { name: 'Eliminar proyecto' }));

    expect(onDelete).toHaveBeenCalledWith(project.id);
  });

  it('keeps navigation outside the editable card and exposes task progress semantically', () => {
    authState.permissions['academy:manage'] = true;
    render(<ProjectCard project={project} index={0} onDelete={vi.fn()} />);

    const detailLink = screen.getByRole('link', { name: 'Abrir proyecto Plan anual' });
    expect(detailLink).toHaveAttribute('href', '/plataforma/projects/project-1?view=list');
    expect(detailLink).not.toContainElement(screen.getByRole('button', { name: 'Eliminar proyecto' }));
    expect(screen.getByRole('progressbar', { name: 'Progreso del proyecto Plan anual' }))
      .toHaveAttribute('aria-valuenow', '0');
  });

  it('does not show delete when only unrelated system configuration is granted', () => {
    authState.permissions['system:config'] = true;

    render(<ProjectCard project={project} index={0} onDelete={vi.fn()} />);

    expect(
      screen.queryByRole('button', { name: 'Eliminar proyecto' })
    ).not.toBeInTheDocument();
  });

  it('renders project and task metrics from the aggregate summary without task records', () => {
    const summarizedProject: ProjectRecord = {
      ...project,
      task_count: 4,
      completed_task_count: 3,
      in_progress_task_count: 1,
      progress_percent: 75,
      health_status: 'at_risk',
    };

    render(<ProjectCard project={summarizedProject} index={0} onDelete={vi.fn()} />);

    expect(screen.getByRole('progressbar', { name: 'Progreso del proyecto Plan anual' }))
      .toHaveAttribute('aria-valuenow', '75');
    expect(screen.getByText('4 tareas')).toBeInTheDocument();
    expect(screen.getByText('3 completadas')).toBeInTheDocument();
    expect(screen.getByText('1 en curso')).toBeInTheDocument();
  });

  it('uses a safe fallback for an invalid persisted project color', () => {
    const invalidColorProject: ProjectRecord = {
      ...project,
      color: 'url(javascript:alert(1))',
    };

    render(<ProjectCard project={invalidColorProject} index={0} />);

    const colorInput = screen.getByLabelText('Color del proyecto Plan anual');
    expect(colorInput).toHaveValue(DEFAULT_PROJECT_COLOR);
    expect(colorInput.parentElement).toHaveStyle({ backgroundColor: DEFAULT_PROJECT_COLOR });
  });
});
