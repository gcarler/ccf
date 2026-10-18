import React from 'react';
import { render, screen, fireEvent, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { describe, it, expect, vi } from 'vitest';
import TaskActivitySection, { computeActivityPmiStats } from './TaskActivitySection';
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
    // El contador de la cabecera es 2 (raíces); "Completadas: 2" en el resumen PMI
    expect(within(screen.getByRole('heading')).getByText('2')).toBeInTheDocument();
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

// ── Gobernanza de Descomposición PMI §6.2 + Ciclo PHVA/PDCA ──

export const pmiActivities: Activity[] = [
  {
    id: 'p1',
    title: 'Revisar diseño',
    completed: false,
    assignee: { name: 'Ana' },
  },
  {
    id: 'p2',
    title: 'Escribir tests',
    completed: true,
    children: [
      {
        id: 'p2-1',
        title: 'Tests unitarios',
        completed: true,
        assignee: { name: 'Beto' },
      },
      {
        id: 'p2-2',
        title: 'Documentar API',
        completed: false,
        children: [
          {
            id: 'p2-2-1',
            title: 'Borrador endpoint',
            completed: false,
          },
        ],
      },
    ],
  },
];

describe('TaskActivitySection — Descomposición PMI §6.2 y PHVA/PDCA', () => {
  const mount = (over?: Partial<{ activities: Activity[]; onNewActivityTitleChange: (v: string) => void }>) =>
    render(
      <TaskActivitySection
        activities={over?.activities ?? pmiActivities}
        newActivityTitle=""
        onNewActivityTitleChange={over?.onNewActivityTitleChange ?? vi.fn()}
        onAddTopLevel={vi.fn()}
        onToggle={vi.fn()}
        onAddChild={vi.fn()}
        onUpdateTitle={vi.fn()}
        onDelete={vi.fn()}
      />,
    );

  it('calcula recurviamente el resumen PMI §6.2 (total, completadas, % avance, brechas y niveles)', () => {
    // 5 nodos (p1, p2, p2-1, p2-2, p2-2-1); completadas: p2 y p2-1 → 40%;
    // pendientes sin responsable: p2-2 y p2-2-1 → 2; profundidad máxima: Nivel 3
    mount();

    const summary = screen.getByTestId('task-activities-pmi-summary');
    const text = () => summary.textContent ?? '';
    expect(text()).toMatch(/Total Nodos:\s*5/);
    expect(text()).toMatch(/Completadas:\s*2/);
    expect(text()).toMatch(/40%/);
    expect(text()).toMatch(/Brechas sin Responsable:\s*2/);
    expect(text()).toMatch(/Nivel 3/);

    // Pureza y matemática de la función pura
    expect(computeActivityPmiStats(pmiActivities)).toEqual({
      totalCount: 5,
      completedCount: 2,
      completionPct: 40,
      unassignedPendingCount: 2,
      maxDepth: 3,
    });
  });

  it('filtra recurvivamente el árbol con las píldoras PENDING, COMPLETED, UNASSIGNED y ALL', () => {
    const { unmount } = mount();
    const filter = screen.getByTestId('task-activities-pmi-filter');
    const clickFilter = (name: string) =>
      fireEvent.click(within(filter).getByRole('button', { name }));

    // PENDING: p1 + sub-rama pendiente (p2 se conserva por tener hijos que cumplen)
    clickFilter('Pendientes');
    expect(screen.getByText('Revisar diseño')).toBeInTheDocument();
    expect(screen.getByText('Escribir tests')).toBeInTheDocument();
    expect(screen.getByText('Documentar API')).toBeInTheDocument();
    // El nivel 3 nace colapsado; se expande explícitamente
    fireEvent.click(screen.getByRole('button', { name: 'Expandir sub-actividades de Documentar API' }));
    expect(screen.getByText('Borrador endpoint')).toBeInTheDocument();
    expect(screen.queryByText('Tests unitarios')).not.toBeInTheDocument();

    // COMPLETED: p2 y p2-1; la rama pendiente se poda
    clickFilter('Completadas');
    expect(screen.queryByText('Revisar diseño')).not.toBeInTheDocument();
    expect(screen.getByText('Escribir tests')).toBeInTheDocument();
    expect(screen.getByText('Tests unitarios')).toBeInTheDocument();
    expect(screen.queryByText('Documentar API')).not.toBeInTheDocument();

    // UNASSIGNED: pendientes sin responsable (p2-2 y p2-2-1) + ancestros que cumplen
    clickFilter('Sin Responsable');
    expect(screen.queryByText('Revisar diseño')).not.toBeInTheDocument();
    expect(screen.getByText('Documentar API')).toBeInTheDocument();
    expect(screen.queryByText('Tests unitarios')).not.toBeInTheDocument();

    // ALL restaura el catálogo completo (expandiendo el nivel 3 colapsado)
    clickFilter('Todas');
    expect(screen.getByText('Revisar diseño')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Expandir sub-actividades de Documentar API' }));
    expect(screen.getByText('Borrador endpoint')).toBeInTheDocument();
    unmount();
  });

  it('prefija la nueva actividad con los 4 pasos canónicos PHVA/PDCA vía onNewActivityTitleChange', () => {
    const onNewActivityTitleChange = vi.fn();
    mount({ onNewActivityTitleChange });

    fireEvent.click(screen.getByTestId('task-activity-preset-plan'));
    expect(onNewActivityTitleChange).toHaveBeenLastCalledWith(
      '[Planificar] Definir alcance técnico y criterios de aceptación',
    );

    fireEvent.click(screen.getByTestId('task-activity-preset-do'));
    expect(onNewActivityTitleChange).toHaveBeenLastCalledWith(
      '[Hacer] Construir e integrar entregable del paquete',
    );

    fireEvent.click(screen.getByTestId('task-activity-preset-check'));
    expect(onNewActivityTitleChange).toHaveBeenLastCalledWith(
      '[Verificar] Ejecutar pruebas QA y validar evidencia DoD',
    );

    fireEvent.click(screen.getByTestId('task-activity-preset-act'));
    expect(onNewActivityTitleChange).toHaveBeenLastCalledWith(
      '[Actuar] Documentar lecciones aprendidas y cierre',
    );
    expect(onNewActivityTitleChange).toHaveBeenCalledTimes(4);
  });

  it('no muestra el resumen ni el filtro PMI cuando no hay actividades', () => {
    mount({ activities: [] });
    expect(screen.queryByTestId('task-activities-pmi-summary')).not.toBeInTheDocument();
    expect(screen.queryByTestId('task-activities-pmi-filter')).not.toBeInTheDocument();
  });
});
