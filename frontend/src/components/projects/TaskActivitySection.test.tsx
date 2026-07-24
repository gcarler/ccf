import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import TaskActivitySection from './TaskActivitySection';
import type { Activity } from './TaskActivitySection';

const activities: Activity[] = [
  { id: 'a1', title: 'Revisar diseño', completed: false },
  { id: 'a2', title: 'Escribir tests', completed: true, children: [
    { id: 'a2-1', title: 'Tests unitarios', completed: true },
  ] },
];

describe('TaskActivitySection', () => {
  it('renders activities list with titles and count', () => {
    render(
      <TaskActivitySection
        activities={activities}
        newActivityTitle=""
        onNewActivityTitleChange={vi.fn()}
        onAddTopLevel={vi.fn()}
        onToggle={vi.fn()}
        onAddChild={vi.fn()}
        onUpdateTitle={vi.fn()}
        onDelete={vi.fn()}
      />
    );
    expect(screen.getByText('Revisar diseño')).toBeInTheDocument();
    expect(screen.getByText('Escribir tests')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('renders empty state when no activities', () => {
    render(
      <TaskActivitySection
        activities={[]}
        newActivityTitle=""
        onNewActivityTitleChange={vi.fn()}
        onAddTopLevel={vi.fn()}
        onToggle={vi.fn()}
        onAddChild={vi.fn()}
        onUpdateTitle={vi.fn()}
        onDelete={vi.fn()}
      />
    );
    expect(screen.getByText('0')).toBeInTheDocument();
  });

  it('calls onAddTopLevel when Enter pressed with text', () => {
    const onAddTopLevel = vi.fn();
    render(
      <TaskActivitySection
        activities={[]}
        newActivityTitle="Nueva act"
        onNewActivityTitleChange={vi.fn()}
        onAddTopLevel={onAddTopLevel}
        onToggle={vi.fn()}
        onAddChild={vi.fn()}
        onUpdateTitle={vi.fn()}
        onDelete={vi.fn()}
      />
    );
    const input = screen.getByPlaceholderText('Añadir actividad...');
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(onAddTopLevel).toHaveBeenCalledTimes(1);
  });
});
