import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import {
  ProjectUpdateProvider,
  useOptionalProjectUpdate,
  useProjectUpdate,
  type ProjectUpdateContextValue,
} from './ProjectUpdateContext';

const mockContextValue: ProjectUpdateContextValue = {
  project: { id: 'proj-1', title: 'Proyecto Test', status: 'active' } as never,
  tasks: [{ id: 't-1', project_id: 'proj-1', title: 'Tarea 1', status: 'todo', priority: 'medium' }],
  phases: [{ slug: 'todo', name: 'Por hacer', color: '#000', order_index: 0 }],
  activities: [],
  loading: false,
  reloadProject: vi.fn().mockResolvedValue(undefined),
  updateTask: vi.fn().mockResolvedValue(undefined),
  createTask: vi.fn().mockResolvedValue(true),
  deleteTask: vi.fn().mockResolvedValue(undefined),
  updateProject: vi.fn().mockResolvedValue(undefined),
};

function ConsumerStrict() {
  const ctx = useProjectUpdate();
  return (
    <div data-testid="strict-consumer">
      {ctx.project?.title} · {ctx.tasks.length} tarea(s) · {ctx.phases.length} fase(s)
    </div>
  );
}

function ConsumerOptional() {
  const ctx = useOptionalProjectUpdate();
  return <div data-testid="optional-consumer">{ctx ? ctx.project?.title : 'no-context'}</div>;
}

describe('ProjectUpdateContext', () => {
  it('provides project, tasks, phases, activities and callbacks inside ProjectUpdateProvider', () => {
    render(
      <ProjectUpdateProvider value={mockContextValue}>
        <ConsumerStrict />
        <ConsumerOptional />
      </ProjectUpdateProvider>,
    );

    expect(screen.getByTestId('strict-consumer')).toHaveTextContent(
      'Proyecto Test · 1 tarea(s) · 1 fase(s)',
    );
    expect(screen.getByTestId('optional-consumer')).toHaveTextContent('Proyecto Test');
  });

  it('throws an error when useProjectUpdate is used outside ProjectUpdateProvider', () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    expect(() => render(<ConsumerStrict />)).toThrow(
      'useProjectUpdate must be used within a ProjectUpdateProvider',
    );
    consoleSpy.mockRestore();
  });

  it('returns null from useOptionalProjectUpdate outside ProjectUpdateProvider', () => {
    render(<ConsumerOptional />);
    expect(screen.getByTestId('optional-consumer')).toHaveTextContent('no-context');
  });
});
