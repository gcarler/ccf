import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import TaskDetailHeader from './TaskDetailHeader';
import type { ProjectTaskRecord } from '@/types/projects';

vi.mock('@/lib/projects/constants', () => ({
  getStatusOption: (val: string) => {
    const map: Record<string, { label: string; dot: string; bg: string; text: string; border: string }> = {
      todo:        { label: 'Pendiente',   dot: '', bg: 'bg-slate-100 dark:bg-white/5', text: 'text-slate-600 dark:text-slate-300', border: '' },
      in_progress: { label: 'En Progreso', dot: '', bg: 'bg-blue-100 dark:bg-blue-900/20', text: 'text-blue-600 dark:text-blue-300', border: '' },
      completed:   { label: 'Completado',  dot: '', bg: 'bg-green-100 dark:bg-green-900/20', text: 'text-green-600 dark:text-green-300', border: '' },
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
});
