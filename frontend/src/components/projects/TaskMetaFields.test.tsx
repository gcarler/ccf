import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import TaskMetaFields from './TaskMetaFields';
import type { ProjectTaskRecord } from '@/types/projects';

vi.mock('@/lib/http', () => ({
  apiFetch: vi.fn().mockResolvedValue({}),
}));

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({ token: 'test-token', user: null, loading: false, isAuthenticated: true }),
}));

afterEach(() => {
  vi.useRealTimers();
});

const mockTask: ProjectTaskRecord = {
  id: 't-123',
  project_id: 'p-456',
  title: 'Tarea de prueba',
  status: 'todo',
  priority: 'medium',
  due_date: '2026-10-22T00:00:00Z',
  node: 'digital',
};

const defaultPriority = { color: 'text-info', dot: 'bg-info', label: 'Media' };

describe('TaskMetaFields', () => {
  it('renders interactive InlineDatePicker without timezone shift (keeps day 22)', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-09-01T12:00:00Z"));
    const onDueDateChange = vi.fn();
    render(
      <TaskMetaFields
        task={mockTask}
        labels={[]}
        onLabelsChange={vi.fn()}
        onAssigneeChange={vi.fn()}
        onDueDateChange={onDueDateChange}
        onPriorityCycle={vi.fn()}
        onNodeCycle={vi.fn()}
        priority={defaultPriority}
        token="test-token"
      />
    );

    // The picker button exists and contains the day 22
    const datePickerButton = screen.getByRole('button', { name: /seleccionar fecha límite/i });
    expect(datePickerButton).toBeInTheDocument();
    expect(datePickerButton.textContent).toMatch(/22/);
    expect(datePickerButton.textContent).not.toMatch(/21 oct/i);
  });

  it('renders fallback calendar format without timezone shift when onDueDateChange is not provided', () => {
    render(
      <TaskMetaFields
        task={mockTask}
        labels={[]}
        onLabelsChange={vi.fn()}
        onAssigneeChange={vi.fn()}
        onPriorityCycle={vi.fn()}
        onNodeCycle={vi.fn()}
        priority={defaultPriority}
        token="test-token"
      />
    );

    const staticDate = screen.getByText(/22/);
    expect(staticDate).toBeInTheDocument();
    expect(screen.queryByText(/21 oct/i)).not.toBeInTheDocument();
  });

  it('renders "Sin fecha límite" when due_date is null and no onDueDateChange', () => {
    const taskWithoutDate = { ...mockTask, due_date: undefined };
    render(
      <TaskMetaFields
        task={taskWithoutDate}
        labels={[]}
        onLabelsChange={vi.fn()}
        onAssigneeChange={vi.fn()}
        onPriorityCycle={vi.fn()}
        onNodeCycle={vi.fn()}
        priority={defaultPriority}
        token="test-token"
      />
    );

    expect(screen.getByText('Sin fecha límite')).toBeInTheDocument();
  });

  it('does not render orphan Nodo Operativo section', () => {
    render(
      <TaskMetaFields
        task={mockTask}
        labels={[]}
        onLabelsChange={vi.fn()}
        onAssigneeChange={vi.fn()}
        onPriorityCycle={vi.fn()}
        priority={defaultPriority}
        token="test-token"
      />
    );

    expect(screen.queryByText('Nodo Operativo')).not.toBeInTheDocument();
    expect(screen.queryByText('Sin nodo')).not.toBeInTheDocument();
  });

  it('renders Componente (EDT) select and allows reassigning component', () => {
    const onComponentChange = vi.fn();
    const mockComponents = [
      { id: 'comp-1', code: 'EDT-1.0', name: 'Arquitectura' },
      { id: 'comp-2', code: 'EDT-2.0', name: 'Frontend' },
    ];
    const taskWithComp: ProjectTaskRecord = { ...mockTask, component_id: 'comp-1' };

    render(
      <TaskMetaFields
        task={taskWithComp}
        labels={[]}
        components={mockComponents}
        onLabelsChange={vi.fn()}
        onAssigneeChange={vi.fn()}
        onPriorityCycle={vi.fn()}
        onComponentChange={onComponentChange}
        priority={defaultPriority}
        token="test-token"
      />
    );

    const compSelect = screen.getByRole('combobox', { name: 'Componente (EDT)' });
    expect(compSelect).toBeInTheDocument();
    expect(compSelect).toHaveValue('comp-1');

    // Change to comp-2
    fireEvent.change(compSelect, { target: { value: 'comp-2' } });
    expect(onComponentChange).toHaveBeenCalledWith('comp-2');

    // Change to empty (Sin componente)
    fireEvent.change(compSelect, { target: { value: '' } });
    expect(onComponentChange).toHaveBeenCalledWith(null);
  });

  it('renders read-only Componente (EDT) label when onComponentChange is not provided', () => {
    const mockComponents = [
      { id: 'comp-1', code: 'EDT-1.0', name: 'Arquitectura' },
    ];
    const taskWithComp: ProjectTaskRecord = { ...mockTask, component_id: 'comp-1' };

    render(
      <TaskMetaFields
        task={taskWithComp}
        labels={[]}
        components={mockComponents}
        onLabelsChange={vi.fn()}
        onAssigneeChange={vi.fn()}
        onPriorityCycle={vi.fn()}
        priority={defaultPriority}
        token="test-token"
      />
    );

    expect(screen.queryByRole('combobox', { name: 'Componente (EDT)' })).not.toBeInTheDocument();
    expect(screen.getByText('Arquitectura')).toBeInTheDocument();
  });

  it('allows creating an EDT component inline and triggers onComponentCreated', async () => {
    const onComponentChange = vi.fn();
    const onComponentCreated = vi.fn();
    const mockComponents = [
      { id: 'comp-1', code: 'EDT-1.0', name: 'Arquitectura' },
    ];
    const { apiFetch } = await import('@/lib/http');
    vi.mocked(apiFetch).mockImplementation((url: string) => {
      if (url.includes('/components')) {
        return Promise.resolve({
          id: 'comp-new',
          code: 'EDT-2.0',
          name: 'Infraestructura',
        });
      }
      return Promise.resolve([]);
    });

    render(
      <TaskMetaFields
        task={mockTask}
        labels={[]}
        components={mockComponents}
        onLabelsChange={vi.fn()}
        onAssigneeChange={vi.fn()}
        onPriorityCycle={vi.fn()}
        onComponentChange={onComponentChange}
        onComponentCreated={onComponentCreated}
        priority={defaultPriority}
        token="test-token"
      />
    );

    const newBtn = screen.getByText('+ Nuevo componente');
    expect(newBtn).toBeInTheDocument();
    fireEvent.click(newBtn);

    expect(screen.getByTestId('meta-inline-edt-form')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Nombre del Componente'), {
      target: { value: 'Infraestructura' },
    });

    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }));

    const { waitFor } = await import('@testing-library/react');
    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        '/projects/p-456/components',
        expect.objectContaining({
          method: 'POST',
          body: { code: 'EDT-2.0', name: 'Infraestructura' },
        })
      );
      expect(onComponentChange).toHaveBeenCalledWith('comp-new');
      expect(onComponentCreated).toHaveBeenCalledWith(
        expect.objectContaining({ id: 'comp-new', name: 'Infraestructura' })
      );
    });
  });
});
