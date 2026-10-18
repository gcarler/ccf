import { fireEvent, render, screen, within } from '@testing-library/react';
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

describe('ProjectCard — Franja Ejecutiva de Gobernanza de Portafolio PMI', () => {
  beforeEach(() => {
    authState.permissions = {};
  });

  it('resuelve el Semáforo RAG por health_override, health_status o tareas vencidas derivadas', () => {
    // Override explícito tiene prioridad
    const { unmount: unmountOverride } = render(
      <ProjectCard
        project={{ ...project, health_override: 'off_track', health_status: 'on_track' }}
        index={0}
      />,
    );
    expect(screen.getByTestId('project-card-pmi-health')).toHaveTextContent('Salud: Crítico');
    unmountOverride();

    // health_status del resumen agregado
    const { unmount: unmountStatus } = render(
      <ProjectCard project={{ ...project, health_status: 'at_risk' }} index={0} />,
    );
    expect(screen.getByTestId('project-card-pmi-health')).toHaveTextContent('Salud: En Riesgo');
    unmountStatus();

    // Derivación por tareas vencidas sin completar: 3 vencidas → Crítico
    const now = Date.now();
    const pastDate = new Date(now - 7 * 24 * 60 * 60 * 1000).toISOString();
    const { unmount: unmountOverdue } = render(
      <ProjectCard
        project={{
          ...project,
          tasks: [
            { id: 't1', project_id: 'project-1', title: 'Vencida 1', status: 'in_progress', due_date: pastDate } as never,
            { id: 't2', project_id: 'project-1', title: 'Vencida 2', status: 'in_progress', due_date: pastDate } as never,
            { id: 't3', project_id: 'project-1', title: 'Vencida 3', status: 'in_progress', due_date: pastDate } as never,
          ],
        }}
        index={0}
      />,
    );
    expect(screen.getByTestId('project-card-pmi-health')).toHaveTextContent('Salud: Crítico');
    expect(screen.getByTestId('project-card-pmi-health')).toHaveClass(
      'text-[hsl(var(--destructive))]',
    );
    unmountOverdue();

    // 1 vencida → En Riesgo
    const { unmount: unmountOneOverdue } = render(
      <ProjectCard
        project={{
          ...project,
          tasks: [
            { id: 't1', project_id: 'project-1', title: 'Vencida 1', status: 'in_progress', due_date: pastDate } as never,
          ],
        }}
        index={0}
      />,
    );
    expect(screen.getByTestId('project-card-pmi-health')).toHaveTextContent('Salud: En Riesgo');
    expect(screen.getByTestId('project-card-pmi-health')).toHaveClass('text-[hsl(var(--warning))]');
    unmountOneOverdue();

    // Sin señales → En Camino
    render(
      <ProjectCard
        project={{
          ...project,
          tasks: [
            { id: 't4', project_id: 'project-1', title: 'Completada', status: 'completed', due_date: pastDate } as never,
          ],
        }}
        index={0}
      />,
    );
    expect(screen.getByTestId('project-card-pmi-health')).toHaveTextContent('Salud: En Camino');
    expect(screen.getByTestId('project-card-pmi-health')).toHaveClass('text-[hsl(var(--success))]');
  });

  it('muestra BAC con CPI y alerta destructiva cuando CPI < 1; Sin Línea Base BAC si no hay presupuesto', () => {
    const { unmount: unmountWithBac } = render(
      <ProjectCard
        project={{
          ...project,
          budget_allocated: 5000,
          budget_summary: {
            project_id: 'project-1',
            budget_allocated: 5000,
            budget_spent: 4000,
            remaining_budget: 1000,
            burn_rate_percent: 80,
            total_expenses_count: 3,
            planned_amount: 0,
            committed_amount: 0,
            paid_amount: 0,
            by_category: {},
            cpi: 0.85,
          },
        }}
        index={0}
      />,
    );
    const budget = screen.getByTestId('project-card-pmi-budget');
    expect(budget).toHaveTextContent(/BAC\s*\$5\.000/);
    expect(budget).toHaveTextContent(/CPI\s*0\.85/);
    expect(budget).toHaveClass('text-[hsl(var(--destructive))]');
    unmountWithBac();

    // CPI saludable aspira al token de éxito
    const { unmount: unmountHealthy } = render(
      <ProjectCard
        project={{
          ...project,
          budget_allocated: 2000,
          budget_summary: {
            project_id: 'project-1',
            budget_allocated: 2000,
            budget_spent: 900,
            remaining_budget: 1100,
            burn_rate_percent: 45,
            total_expenses_count: 2,
            planned_amount: 0,
            committed_amount: 0,
            paid_amount: 0,
            by_category: {},
            cpi: 1.12,
          },
        }}
        index={0}
      />,
    );
    expect(screen.getByTestId('project-card-pmi-budget')).toHaveTextContent(/CPI\s*1\.12/);
    expect(screen.getByTestId('project-card-pmi-budget')).toHaveClass('text-[hsl(var(--success))]');
    unmountHealthy();

    // Sin BAC → mensaje muted
    render(<ProjectCard project={{ ...project }} index={0} />);
    expect(screen.getByTestId('project-card-pmi-budget')).toHaveTextContent('Sin Línea Base BAC');
    expect(screen.getByTestId('project-card-pmi-budget')).toHaveClass(
      'text-[hsl(var(--muted-foreground))]',
    );
  });

  it('refleja la gobernanza PM (RACI): asignado vs propietario ausente', () => {
    const { unmount: unmountWithPm } = render(
      <ProjectCard project={{ ...project, owner_id: 'user-pm-1' }} index={0} />,
    );
    expect(screen.getByTestId('project-card-pmi-sponsor')).toHaveTextContent('PM Asignado');
    expect(screen.getByTestId('project-card-pmi-sponsor')).toHaveClass('text-[hsl(var(--success))]');
    unmountWithPm();

    render(<ProjectCard project={{ ...project, owner_id: null }} index={0} />);
    expect(screen.getByTestId('project-card-pmi-sponsor')).toHaveTextContent('Sin PM (RACI)');
    expect(screen.getByTestId('project-card-pmi-sponsor')).toHaveClass('text-[hsl(var(--warning))]');
  });

  it('preserva la suite original: la franja ejecutiva convive con métricas y semáforo del resumen', () => {
    render(
      <ProjectCard
        project={{
          ...project,
          task_count: 4,
          completed_task_count: 3,
          progress_percent: 75,
          health_status: 'at_risk',
          owner_id: 'user-pm-1',
          budget_allocated: 1000,
        }}
        index={0}
      />,
    );
    const strip = screen.getByTestId('project-card-pmi-strip');
    expect(within(strip).getByTestId('project-card-pmi-health')).toHaveTextContent('Salud: En Riesgo');
    expect(within(strip).getByTestId('project-card-pmi-budget')).toHaveTextContent(/BAC\s*\$1\.000/);
    expect(within(strip).getByTestId('project-card-pmi-sponsor')).toHaveTextContent('PM Asignado');

    // Métricas agregadas intactas
    expect(screen.getByText('4 tareas')).toBeInTheDocument();
    expect(screen.getByRole('progressbar', { name: 'Progreso del proyecto Plan anual' }))
      .toHaveAttribute('aria-valuenow', '75');
  });
});
