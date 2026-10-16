import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import TaskLabelManager from './TaskLabelManager';
import type { ProjectTaskRecord } from '@/types/projects';

vi.mock('@/lib/http', () => ({
  apiFetch: vi.fn().mockResolvedValue({}),
}));

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({ token: 'test-token', user: null, loading: false, isAuthenticated: true }),
}));

vi.mock('@/context/ProjectUpdateContext', () => ({
  useOptionalProjectUpdate: () => ({
    project: { id: 'p1', title: 'Test Project' },
    tasks: [
      { id: 't2', title: 'Otra tarea', labels: ['Infraestructura', 'Seguridad'] },
    ],
    phases: [],
    activities: [],
    loading: false,
    reloadProject: vi.fn(),
    createTask: vi.fn(),
    updateTask: vi.fn(),
    deleteTask: vi.fn(),
    updateProject: vi.fn(),
  }),
}));

const task: ProjectTaskRecord = {
  id: 't1',
  project_id: 'p1',
  title: 'Test task',
  status: 'todo',
  priority: 'medium',
};

describe('TaskLabelManager', () => {
  it('renders label chips', () => {
    render(
      <TaskLabelManager task={task} labels={['Urgente', 'Alabanza']} onLabelsChange={vi.fn()} token="test-token" />
    );
    expect(screen.getByText('Urgente')).toBeInTheDocument();
    expect(screen.getByText('Alabanza')).toBeInTheDocument();
  });

  it('renders add button', () => {
    render(
      <TaskLabelManager task={task} labels={[]} onLabelsChange={vi.fn()} token="test-token" />
    );
    expect(screen.getByText('Añadir etiqueta')).toBeInTheDocument();
  });

  it('shows dynamic suggestions and gestionar etiquetas button when opened', () => {
    const onManageLabels = vi.fn();
    render(
      <TaskLabelManager
        task={task}
        labels={[]}
        onLabelsChange={vi.fn()}
        token="test-token"
        onManageLabels={onManageLabels}
      />
    );

    const addBtn = screen.getByText('Añadir etiqueta');
    fireEvent.click(addBtn);

    // Suggestions from other tasks in project (Infraestructura, Seguridad) and defaults
    expect(screen.getByText('Infraestructura')).toBeInTheDocument();
    expect(screen.getByText('Seguridad')).toBeInTheDocument();
    expect(screen.getByText('Alabanza')).toBeInTheDocument();

    const manageBtn = screen.getByText('Gestionar etiquetas');
    expect(manageBtn).toBeInTheDocument();

    fireEvent.click(manageBtn);
    expect(onManageLabels).toHaveBeenCalledTimes(1);
  });

  it('adds label from suggestion click', async () => {
    const onLabelsChange = vi.fn();
    render(
      <TaskLabelManager
        task={task}
        labels={[]}
        onLabelsChange={onLabelsChange}
        token="test-token"
      />
    );

    fireEvent.click(screen.getByText('Añadir etiqueta'));
    const suggestionBtn = screen.getByText('Infraestructura');
    fireEvent.click(suggestionBtn);

    expect(onLabelsChange).toHaveBeenCalledWith(['Infraestructura']);
  });
});
