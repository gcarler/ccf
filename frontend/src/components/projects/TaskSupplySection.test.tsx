import React, { useState } from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
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
});
