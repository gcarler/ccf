import React, { useState } from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { axe } from 'jest-axe';
import { describe, it, expect, vi } from 'vitest';
import TaskSupplySection from './TaskSupplySection';
import { apiFetch } from '@/lib/http';
import type { ProjectTaskRecord, TaskSupplyRecord } from '@/types/projects';

vi.mock('@/lib/http', () => ({
  apiFetch: vi.fn().mockResolvedValue([]),
}));

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({ token: 'test-token', user: null, loading: false, isAuthenticated: true }),
}));

const task: ProjectTaskRecord = {
  id: 't1',
  project_id: 'p1',
  title: 'Test task',
  status: 'todo',
  priority: 'medium',
};

const supplies: TaskSupplyRecord[] = [
  { id: 's1', task_id: 't1', item_name: 'Cable HDMI', quantity: 3, status: 'pending' },
  { id: 's2', task_id: 't1', item_name: 'Proyector', quantity: 1, status: 'ready' },
];

describe('TaskSupplySection', () => {
  it('labels every supply field/action and passes axe', async () => {
    const { container } = render(
      <TaskSupplySection task={task} supplies={supplies} onSuppliesChange={vi.fn()} token="test-token" />,
    );

    expect(screen.getByRole('heading', { name: 'Insumos 2' })).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: 'Nombre del insumo Cable HDMI' })).toBeInTheDocument();
    expect(screen.getByRole('spinbutton', { name: 'Cantidad de Cable HDMI' })).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: 'Estado de Cable HDMI' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Eliminar insumo: Cable HDMI' })).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: 'Nombre del nuevo insumo' })).toBeInTheDocument();
    expect(screen.getByRole('spinbutton', { name: 'Cantidad del nuevo insumo' })).toBeInTheDocument();
    expect((await axe(container)).violations).toEqual([]);
  });

  it('renders supplies list with names and count', () => {
    render(
      <TaskSupplySection task={task} supplies={supplies} onSuppliesChange={vi.fn()} token="test-token" />
    );
    expect(screen.getByDisplayValue('Cable HDMI')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Proyector')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('renders empty state when no supplies', () => {
    render(
      <TaskSupplySection task={task} supplies={[]} onSuppliesChange={vi.fn()} token="test-token" />
    );
    expect(screen.getByText('Sin insumos registrados.')).toBeInTheDocument();
  });

  it('add button is disabled when name is empty', () => {
    render(
      <TaskSupplySection task={task} supplies={[]} onSuppliesChange={vi.fn()} token="test-token" />
    );
    const button = screen.getByRole('button', { name: /Agregar/ });
    expect(button).toBeDisabled();
  });

  it('persists an inline name edit even when the parent mirrors the optimistic draft into task.supplies', async () => {
    const onActivityCreated = vi.fn();
    const originalSupply = supplies[0];
    const updatedSupply = { ...originalSupply, item_name: 'Cable USB-C' };
    vi.mocked(apiFetch).mockResolvedValueOnce(updatedSupply);

    function Harness() {
      const [currentSupplies, setCurrentSupplies] = useState(supplies);
      const currentTask = { ...task, supplies: currentSupplies };
      return (
        <TaskSupplySection
          task={currentTask}
          supplies={currentSupplies}
          onSuppliesChange={setCurrentSupplies}
          token="test-token"
          onActivityCreated={onActivityCreated}
        />
      );
    }

    render(<Harness />);
    const nameInput = screen.getByRole('textbox', { name: 'Nombre del insumo Cable HDMI' });
    fireEvent.change(nameInput, { target: { value: 'Cable USB-C' } });
    fireEvent.blur(nameInput);

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        '/projects/p1/tasks/t1/supplies/s1',
        expect.objectContaining({ method: 'PATCH', body: { item_name: 'Cable USB-C' } }),
      );
    });
    expect(onActivityCreated).toHaveBeenCalledTimes(1);
  });

  it('rolls back an optimistic edit and announces the failure when the PATCH is rejected', async () => {
    vi.mocked(apiFetch).mockRejectedValueOnce(new Error('offline'));

    function Harness() {
      const [currentSupplies, setCurrentSupplies] = useState(supplies);
      return (
        <TaskSupplySection
          task={{ ...task, supplies: currentSupplies }}
          supplies={currentSupplies}
          onSuppliesChange={setCurrentSupplies}
          token="test-token"
        />
      );
    }

    render(<Harness />);
    const nameInput = screen.getByRole('textbox', { name: 'Nombre del insumo Cable HDMI' });
    fireEvent.change(nameInput, { target: { value: 'Cable USB-C' } });
    fireEvent.blur(nameInput);

    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo actualizar el insumo.');
    expect(screen.getByRole('textbox', { name: 'Nombre del insumo Cable HDMI' })).toHaveValue('Cable HDMI');
  });

  it('displays unit_cost, total_cost, linked AC expense badge and sends cost fields on creation', async () => {
    const costSupplies: TaskSupplyRecord[] = [
      {
        id: 's1',
        task_id: 't1',
        item_name: 'Micrófono Inalámbrico',
        quantity: 2,
        unit_cost: 150,
        total_cost: 300,
        auto_create_expense: true,
        linked_expense_id: 'exp-99',
        status: 'purchased',
      },
    ];
    const createdSupply: TaskSupplyRecord = {
      id: 's2',
      task_id: 't1',
      item_name: 'Consola Audio',
      quantity: 1,
      unit_cost: 500,
      total_cost: 500,
      auto_create_expense: true,
      linked_expense_id: 'exp-100',
      status: 'pending',
    };
    vi.mocked(apiFetch).mockResolvedValueOnce(createdSupply);

    render(
      <TaskSupplySection
        task={task}
        supplies={costSupplies}
        onSuppliesChange={vi.fn()}
        token="test-token"
      />,
    );

    expect(screen.getByText(/Costo Total Insumos: \$300/i)).toBeInTheDocument();
    expect(screen.getByText('Gasto sincronizado (exp-99)')).toBeInTheDocument();

    fireEvent.change(screen.getByRole('textbox', { name: 'Nombre del nuevo insumo' }), {
      target: { value: 'Consola Audio' },
    });
    fireEvent.change(screen.getByRole('spinbutton', { name: 'Costo unitario del nuevo insumo' }), {
      target: { value: '500' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Agregar/ }));

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        '/projects/p1/tasks/t1/supplies',
        expect.objectContaining({
          method: 'POST',
          body: expect.objectContaining({
            item_name: 'Consola Audio',
            quantity: 1,
            unit_cost: 500,
            total_cost: 500,
            auto_create_expense: true,
          }),
        }),
      );
    });
  });

  it('shows PMI procurement stages, physical and AC percentages, and package budget overrun', async () => {
    const procurementSupplies: TaskSupplyRecord[] = [
      { id: 's-pending', task_id: 't1', item_name: 'Pendiente', quantity: 1, unit_cost: 100, total_cost: 100, status: 'pending' },
      { id: 's-ordered', task_id: 't1', item_name: 'Ordenado', quantity: 1, unit_cost: 300, total_cost: 300, status: 'ordered' },
      { id: 's-received', task_id: 't1', item_name: 'Recibido', quantity: 1, unit_cost: 400, total_cost: 400, status: 'received' },
      { id: 's-imputed', task_id: 't1', item_name: 'Imputado', quantity: 1, unit_cost: 200, total_cost: 200, status: 'purchased', linked_expense_id: 'exp-200' },
    ];
    const overBudgetTask = { ...task, budget_allocated: 800 };
    const { container } = render(
      <TaskSupplySection
        task={overBudgetTask}
        supplies={procurementSupplies}
        onSuppliesChange={vi.fn()}
        token="test-token"
      />,
    );

    expect(screen.getByRole('heading', {
      name: 'Control PMI de Recursos Físicos y Adquisiciones (Planificado → Comprometido → Imputado en AC)',
    })).toBeInTheDocument();
    const procurementControl = screen.getByRole('region', {
      name: 'Control PMI de Recursos Físicos y Adquisiciones (Planificado → Comprometido → Imputado en AC)',
    });
    expect(within(procurementControl).getByText('$100')).toBeInTheDocument();
    expect(within(procurementControl).getByText('$300')).toBeInTheDocument();
    expect(within(procurementControl).getByText('$600')).toBeInTheDocument();
    expect(within(procurementControl).getByText('60.0% del total')).toBeInTheDocument();
    expect(within(procurementControl).getByText(/Recepción física:/)).toHaveTextContent('$400 · 40.0%');
    expect(within(procurementControl).getByText(/Imputado en AC por gasto vinculado:/)).toHaveTextContent('$200 · 20.0%');
    expect(procurementControl).toHaveTextContent('$1.000 / $800');
    expect(within(procurementControl).getByText('125.0% del presupuesto')).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveTextContent('Exceso sobre Presupuesto del Paquete');
    expect((await axe(container)).violations).toEqual([]);
  });

  it('shows the package budget control even when no supplies have been added', () => {
    render(
      <TaskSupplySection
        task={{ ...task, budget_allocated: 1000 }}
        supplies={[]}
        onSuppliesChange={vi.fn()}
        token="test-token"
      />,
    );

    expect(screen.getByRole('heading', {
      name: 'Control PMI de Recursos Físicos y Adquisiciones (Planificado → Comprometido → Imputado en AC)',
    })).toBeInTheDocument();
    expect(screen.getByRole('region', {
      name: 'Control PMI de Recursos Físicos y Adquisiciones (Planificado → Comprometido → Imputado en AC)',
    })).toHaveTextContent('$0 / $1.000');
  });
});
