import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { axe } from 'jest-axe';
import TaskDetailHeader from './TaskDetailHeader';
import type { ProjectTaskRecord } from '@/types/projects';

const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}));

vi.mock('@/lib/projects/constants', () => ({
  getStatusOption: (val: string) => {
    // Fixture normalizada a tokens semánticos del Design System (rev-ui B-T1-13102026)
    const map: Record<string, { label: string; dot: string; bg: string; text: string; border: string }> = {
      todo:        { label: 'Pendiente',   dot: '', bg: 'bg-[hsl(var(--surface-2))]', text: 'text-[hsl(var(--muted-foreground))]', border: '' },
      in_progress: { label: 'En Progreso', dot: '', bg: 'bg-[hsl(var(--primary)/0.1)]', text: 'text-[hsl(var(--primary))]', border: '' },
      completed:   { label: 'Completado',  dot: '', bg: 'bg-[hsl(var(--success)/0.1)]', text: 'text-[hsl(var(--success))]', border: '' },
    };
    return map[val] ?? map.todo;
  },
}));

const task: ProjectTaskRecord = {
  id: 't1',
  project_id: 'p1',
  title: 'Diseñar interfaz',
  status: 'in_progress',
  priority: 'high',
};

describe('TaskDetailHeader', () => {
  it('renders title, breadcrumbs, and status chip', () => {
    render(
      <TaskDetailHeader
        task={task}
        projectTitle="CCF App"
        title="Diseñar interfaz"
        saving={false}
        uploading={false}
        starred={false}
        error={null}
        onClose={vi.fn()}
        onTitleChange={vi.fn()}
        onSave={vi.fn()}
        onStatusCycle={vi.fn()}
        onFileClick={vi.fn()}
        onStarToggle={vi.fn()}
        onExpandToggle={vi.fn()}
        onDeleteTask={vi.fn()}
      />
    );
    expect(screen.getByText('CCF App')).toBeInTheDocument();
    expect(screen.getAllByText('Diseñar interfaz').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('En Progreso')).toBeInTheDocument();
  });

  it('expone nombres accesibles para las acciones y el título editable', async () => {
    const { container } = render(
      <TaskDetailHeader
        task={task}
        projectTitle="CCF App"
        title="Diseñar interfaz"
        saving={false}
        uploading={false}
        starred={false}
        error={null}
        onClose={vi.fn()}
        onTitleChange={vi.fn()}
        onSave={vi.fn()}
        onStatusCycle={vi.fn()}
        onFileClick={vi.fn()}
        onStarToggle={vi.fn()}
        onExpandToggle={vi.fn()}
        onDeleteTask={vi.fn()}
      />,
    );

    expect(screen.getByRole('button', { name: 'Cerrar detalle de actividad' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Marcar actividad como favorita' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Cambiar estado de la actividad. Estado actual: En Progreso' })).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: 'Título de la actividad' })).toBeInTheDocument();
    expect((await axe(container)).violations).toEqual([]);
  });

  it('el botón clip (onFileClick) dispara la selección de archivos (QA-003)', () => {
    const onFileClick = vi.fn();
    render(
      <TaskDetailHeader
        task={task}
        projectTitle="CCF App"
        title="Tarea"
        saving={false}
        uploading={false}
        starred={false}
        error={null}
        onClose={vi.fn()}
        onTitleChange={vi.fn()}
        onSave={vi.fn()}
        onStatusCycle={vi.fn()}
        onFileClick={onFileClick}
        onStarToggle={vi.fn()}
        onExpandToggle={vi.fn()}
        onDeleteTask={vi.fn()}
      />
    );
    const clipBtn = screen.getByTitle('Adjuntar archivo');
    fireEvent.click(clipBtn);
    expect(onFileClick).toHaveBeenCalledTimes(1);
  });

  it('el clip se deshabilita y muestra spinner mientras uploading=true', () => {
    const onFileClick = vi.fn();
    render(
      <TaskDetailHeader
        task={task}
        projectTitle="CCF App"
        title="Tarea"
        saving={false}
        uploading={true}
        starred={false}
        error={null}
        onClose={vi.fn()}
        onTitleChange={vi.fn()}
        onSave={vi.fn()}
        onStatusCycle={vi.fn()}
        onFileClick={onFileClick}
        onStarToggle={vi.fn()}
        onExpandToggle={vi.fn()}
        onDeleteTask={vi.fn()}
      />
    );
    expect(screen.getByTitle('Subiendo archivo')).toBeDisabled();
  });

  it('calls onClose when close button clicked', () => {
    const onClose = vi.fn();
    render(
      <TaskDetailHeader
        task={task}
        projectTitle="CCF App"
        title="Tarea"
        saving={false}
        uploading={false}
        starred={false}
        error={null}
        onClose={onClose}
        onTitleChange={vi.fn()}
        onSave={vi.fn()}
        onStatusCycle={vi.fn()}
        onFileClick={vi.fn()}
        onStarToggle={vi.fn()}
        onExpandToggle={vi.fn()}
        onDeleteTask={vi.fn()}
      />
    );
    const closeBtn = screen.getByTitle('Cerrar panel');
    fireEvent.click(closeBtn);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('navigates to /plataforma/projects when Home icon is clicked', () => {
    render(
      <TaskDetailHeader
        task={task}
        projectTitle="CCF App"
        title="Tarea"
        saving={false}
        uploading={false}
        starred={false}
        error={null}
        onClose={vi.fn()}
        onTitleChange={vi.fn()}
        onSave={vi.fn()}
        onStatusCycle={vi.fn()}
        onFileClick={vi.fn()}
        onStarToggle={vi.fn()}
        onExpandToggle={vi.fn()}
        onDeleteTask={vi.fn()}
      />
    );
    const homeBtn = screen.getByRole('button', { name: 'Ir al listado de proyectos' });
    fireEvent.click(homeBtn);
    expect(mockPush).toHaveBeenCalledWith('/plataforma/projects');
  });

  it('triggers onVerRutaClick and onClose when projectTitle breadcrumb is clicked', () => {
    const onVerRutaClick = vi.fn();
    const onClose = vi.fn();
    render(
      <TaskDetailHeader
        task={task}
        projectTitle="CCF App"
        title="Tarea"
        saving={false}
        uploading={false}
        starred={false}
        error={null}
        onClose={onClose}
        onTitleChange={vi.fn()}
        onSave={vi.fn()}
        onStatusCycle={vi.fn()}
        onFileClick={vi.fn()}
        onStarToggle={vi.fn()}
        onExpandToggle={vi.fn()}
        onDeleteTask={vi.fn()}
        onVerRutaClick={onVerRutaClick}
      />
    );
    const projBtn = screen.getByRole('button', { name: 'Ir al proyecto: CCF App' });
    fireEvent.click(projBtn);
    expect(onVerRutaClick).toHaveBeenCalledTimes(1);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('triggers onVerRutaClick when Ver Ruta button is clicked', () => {
    const onVerRutaClick = vi.fn();
    render(
      <TaskDetailHeader
        task={task}
        projectTitle="CCF App"
        title="Tarea"
        saving={false}
        uploading={false}
        starred={false}
        error={null}
        onClose={vi.fn()}
        onTitleChange={vi.fn()}
        onSave={vi.fn()}
        onStatusCycle={vi.fn()}
        onFileClick={vi.fn()}
        onStarToggle={vi.fn()}
        onExpandToggle={vi.fn()}
        onDeleteTask={vi.fn()}
        onVerRutaClick={onVerRutaClick}
      />
    );
    const verRutaBtn = screen.getByRole('button', { name: 'Ver ruta jerárquica de la actividad' });
    fireEvent.click(verRutaBtn);
    expect(onVerRutaClick).toHaveBeenCalledTimes(1);
  });

  it('renders PMI executive strip badges (WP vs Nodo Resumen EDT, Rule 0/50/100 credit, and schedule status)', () => {
    const { rerender } = render(
      <TaskDetailHeader
        task={{
          ...task,
          status: 'todo',
          due_date: '2020-01-01',
          subtasks: [],
        }}
        projectTitle="CCF App"
        title="Tarea"
        saving={false}
        uploading={false}
        starred={false}
        error={null}
        onClose={vi.fn()}
        onTitleChange={vi.fn()}
        onSave={vi.fn()}
        onStatusCycle={vi.fn()}
        onFileClick={vi.fn()}
        onStarToggle={vi.fn()}
        onExpandToggle={vi.fn()}
        onDeleteTask={vi.fn()}
      />
    );

    expect(screen.getByTestId('task-header-pmi-strip')).toBeInTheDocument();
    expect(screen.getByTestId('task-header-pmi-node-type')).toHaveTextContent('Paquete de Trabajo (WP)');
    expect(screen.getByTestId('task-header-pmi-earned-rule')).toHaveTextContent('Crédito EVM: 0%');
    expect(screen.getByTestId('task-header-pmi-schedule-badge')).toHaveTextContent('Plazo Vencido');

    rerender(
      <TaskDetailHeader
        task={{
          ...task,
          status: 'in_progress',
          due_date: '2099-12-31',
          subtasks: [
            {
              id: 'sub-1',
              project_id: 'p1',
              title: 'Subtarea',
              status: 'todo',
              priority: 'medium',
            },
          ],
        }}
        projectTitle="CCF App"
        title="Tarea"
        saving={false}
        uploading={false}
        starred={false}
        error={null}
        onClose={vi.fn()}
        onTitleChange={vi.fn()}
        onSave={vi.fn()}
        onStatusCycle={vi.fn()}
        onFileClick={vi.fn()}
        onStarToggle={vi.fn()}
        onExpandToggle={vi.fn()}
        onDeleteTask={vi.fn()}
      />
    );

    expect(screen.getByTestId('task-header-pmi-node-type')).toHaveTextContent('Nodo Resumen EDT');
    expect(screen.getByTestId('task-header-pmi-earned-rule')).toHaveTextContent('Crédito EVM: 50%');
    expect(screen.getByTestId('task-header-pmi-schedule-badge')).toHaveTextContent('En Plazo');

    rerender(
      <TaskDetailHeader
        task={{
          ...task,
          status: 'completed',
          due_date: '2020-01-01',
          subtasks: [],
        }}
        projectTitle="CCF App"
        title="Tarea"
        saving={false}
        uploading={false}
        starred={false}
        error={null}
        onClose={vi.fn()}
        onTitleChange={vi.fn()}
        onSave={vi.fn()}
        onStatusCycle={vi.fn()}
        onFileClick={vi.fn()}
        onStarToggle={vi.fn()}
        onExpandToggle={vi.fn()}
        onDeleteTask={vi.fn()}
      />
    );

    expect(screen.getByTestId('task-header-pmi-earned-rule')).toHaveTextContent('Crédito EVM: 100%');
    expect(screen.queryByTestId('task-header-pmi-schedule-badge')).not.toBeInTheDocument();
  });
});
