import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
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
  it('names activity actions, supports keyboard editing, and has no axe violations', async () => {
    const onUpdateTitle = vi.fn();
    const user = userEvent.setup();
    const { container } = render(
      <TaskActivitySection
        activities={activities}
        newActivityTitle=""
        onNewActivityTitleChange={vi.fn()}
        onAddTopLevel={vi.fn()}
        onToggle={vi.fn()}
        onAddChild={vi.fn()}
        onUpdateTitle={onUpdateTitle}
        onDelete={vi.fn()}
      />,
    );

    expect(screen.getByRole('button', { name: 'Completar actividad: Revisar diseño' })).toHaveAttribute('aria-pressed', 'false');
    expect(screen.getByRole('button', { name: 'Marcar como pendiente: Escribir tests' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: 'Contraer sub-actividades de Escribir tests' })).toHaveAttribute('aria-expanded', 'true');
    expect(screen.queryByRole('button', { name: 'Contraer sub-actividades de Revisar diseño' })).not.toBeInTheDocument();
    const addChildButton = screen.getByRole('button', { name: 'Añadir sub-actividad a Revisar diseño' });
    const deleteButton = screen.getByRole('button', { name: 'Eliminar actividad: Revisar diseño' });
    expect(addChildButton).toHaveClass('opacity-100', 'md:group-focus-within:opacity-100');
    expect(deleteButton).toHaveClass('opacity-100', 'md:group-focus-within:opacity-100');

    await user.click(screen.getByRole('button', { name: 'Editar actividad: Revisar diseño' }));
    const titleInput = screen.getByRole('textbox', { name: 'Editar actividad: Revisar diseño' });
    await user.clear(titleInput);
    await user.type(titleInput, 'Revisar accesibilidad');
    await user.keyboard('{Escape}');
    expect(titleInput).not.toBeInTheDocument();
    expect(onUpdateTitle).not.toHaveBeenCalled();
    expect((await axe(container)).violations).toEqual([]);
  });

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

  it('persists an edited activity once on Enter', async () => {
    const onUpdateTitle = vi.fn();
    const user = userEvent.setup();
    render(
      <TaskActivitySection
        activities={activities}
        newActivityTitle=""
        onNewActivityTitleChange={vi.fn()}
        onAddTopLevel={vi.fn()}
        onToggle={vi.fn()}
        onAddChild={vi.fn()}
        onUpdateTitle={onUpdateTitle}
        onDelete={vi.fn()}
      />,
    );

    await user.click(screen.getByRole('button', { name: 'Editar actividad: Revisar diseño' }));
    const titleInput = screen.getByRole('textbox', { name: 'Editar actividad: Revisar diseño' });
    await user.clear(titleInput);
    await user.type(titleInput, 'Revisar accesibilidad');
    await user.keyboard('{Enter}');

    expect(onUpdateTitle).toHaveBeenCalledTimes(1);
    expect(onUpdateTitle).toHaveBeenCalledWith('a1', 'Revisar accesibilidad');
  });
});
