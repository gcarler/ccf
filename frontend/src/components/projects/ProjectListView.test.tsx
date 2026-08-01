import React from 'react';
import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMockTask } from '@/test-utils/factories';
import type { PhaseDef } from '@/context/ProjectUpdateContext';
import ProjectListView from './ProjectListView';

vi.mock('@/context/SidebarLayerContext', () => ({
  useSidebarLayers: () => ({
    openLayer: vi.fn(),
    setRightMode: vi.fn(),
  }),
}));

vi.mock('@/components/ui/inline-editors', () => ({
  InlineStatusPicker: ({
    value,
    phases,
    onChange,
  }: {
    value: string;
    phases?: PhaseDef[];
    onChange: (value: string) => void;
  }) => (
    <button
      type="button"
      aria-label="Cambiar estado"
      onClick={() => onChange(phases?.[1]?.slug ?? value)}
    >
      {value}
    </button>
  ),
  InlinePriorityPicker: ({ value }: { value: string }) => <span>{value}</span>,
  InlineDatePicker: ({ value }: { value: string | null }) => <span>{value ?? 'Sin fecha'}</span>,
  InlineUserPicker: ({ value }: { value: string | null }) => <span>{value ?? 'Sin asignar'}</span>,
}));

describe('ProjectListView', () => {
  const phases: PhaseDef[] = [
    { slug: 'backlog', name: 'Por planificar', color: '#64748b', order_index: 0 },
    { slug: 'review_custom', name: 'Revisión pastoral', color: '#f59e0b', order_index: 1 },
  ];

  it('groups tasks using the project custom phase label', () => {
    render(
      <ProjectListView
        tasks={[createMockTask({ id: 'task-1', title: 'Preparar reunión', status: 'backlog' })]}
        phaseDefs={phases}
        onOpenTask={vi.fn()}
        onAddTask={vi.fn()}
        onTaskUpdate={vi.fn()}
      />,
    );

    expect(screen.getByText('Por planificar')).toBeInTheDocument();
    expect(screen.getByText('Preparar reunión')).toBeInTheDocument();
  });

  it('delegates custom phase status changes to the parent callback', async () => {
    const onTaskUpdate = vi.fn();
    render(
      <ProjectListView
        tasks={[createMockTask({ id: 'task-1', title: 'Preparar reunión', status: 'backlog' })]}
        phaseDefs={phases}
        onOpenTask={vi.fn()}
        onAddTask={vi.fn()}
        onTaskUpdate={onTaskUpdate}
      />,
    );

    await userEvent.click(screen.getByRole('button', { name: 'Cambiar estado' }));

    expect(onTaskUpdate).toHaveBeenCalledWith('task-1', { status: 'review_custom' });
  });
});
