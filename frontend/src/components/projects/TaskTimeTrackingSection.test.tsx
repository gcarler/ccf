import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { axe } from 'jest-axe';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { apiFetch } from '@/lib/http';
import type { ProjectTaskRecord, ProjectTimeLog } from '@/types/projects';
import TaskTimeTrackingSection from './TaskTimeTrackingSection';

vi.mock('@/lib/http', () => ({ apiFetch: vi.fn() }));

const task: ProjectTaskRecord = {
  id: 'task-1',
  project_id: 'project-1',
  title: 'Preparar encuentro',
  status: 'todo',
  priority: 'medium',
};

const log: ProjectTimeLog = {
  id: 'log-1',
  project_id: 'project-1',
  task_id: 'task-1',
  persona_id: 'person-1',
  persona_name: 'Ana Pérez',
  hours: 1.5,
  date: '2026-10-04T12:00:00Z',
  description: 'Preparación de materiales',
  is_billable: true,
  created_at: '2026-10-04T12:00:00Z',
  updated_at: '2026-10-04T12:00:00Z',
};

describe('TaskTimeTrackingSection accessibility and feedback', () => {
  beforeEach(() => {
    vi.mocked(apiFetch).mockReset();
  });

  it('labels the section, form controls and per-entry action, with no axe violations', async () => {
    vi.mocked(apiFetch).mockResolvedValue([log]);
    const { container } = render(
      <TaskTimeTrackingSection task={task} token="test-token" />,
    );

    await screen.findByText('Preparación de materiales');
    expect(screen.getByRole('heading', { name: /Tiempo Dedicado/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Eliminar registro de 1.50 horas: Preparación de materiales' })).toBeInTheDocument();

    await screen.getByRole('button', { name: 'Registrar horas' }).click();
    expect(screen.getByRole('spinbutton', { name: 'Horas dedicadas *' })).toBeInTheDocument();
    expect(screen.getByRole('checkbox', { name: 'Facturable' })).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: 'Descripción de lo realizado' })).toBeInTheDocument();
    expect((await axe(container)).violations).toEqual([]);
  });

  it('announces recoverable load failures instead of silently rendering an empty list', async () => {
    vi.mocked(apiFetch).mockRejectedValueOnce(new Error('offline'));
    render(<TaskTimeTrackingSection task={task} token="test-token" />);

    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudieron cargar los registros de tiempo.');
    await waitFor(() => expect(screen.queryByRole('status')).not.toBeInTheDocument());
  });

  it('requires confirmation before deleting a task time entry', async () => {
    vi.mocked(apiFetch).mockResolvedValue([log]);
    render(<TaskTimeTrackingSection task={task} token="test-token" />);
    fireEvent.click(await screen.findByRole('button', { name: 'Eliminar registro de 1.50 horas: Preparación de materiales' }));

    expect(await screen.findByRole('complementary', { name: 'Eliminar registro de tiempo' })).toHaveTextContent('Preparación de materiales');
    expect(vi.mocked(apiFetch).mock.calls.some(([, options]) => options?.method === 'DELETE')).toBe(false);
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }));
    await waitFor(() => expect(screen.queryByRole('complementary', { name: 'Eliminar registro de tiempo' })).not.toBeInTheDocument());
    expect(screen.getByText('Preparación de materiales')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Eliminar registro de 1.50 horas: Preparación de materiales' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Eliminar registro' }));
    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith(
      '/projects/project-1/time-logs/log-1',
      expect.objectContaining({ method: 'DELETE', token: 'test-token' }),
    ));
  });

  it('keeps time entry confirmation available when deleting fails', async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce([log]);
    render(<TaskTimeTrackingSection task={task} token="test-token" />);
    await screen.findByText('Preparación de materiales');
    vi.mocked(apiFetch).mockRejectedValueOnce(new Error('offline'));
    fireEvent.click(await screen.findByRole('button', { name: 'Eliminar registro de 1.50 horas: Preparación de materiales' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Eliminar registro' }));

    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith(
      '/projects/project-1/time-logs/log-1',
      expect.objectContaining({ method: 'DELETE', token: 'test-token' }),
    ));
    expect(screen.getByRole('complementary', { name: 'Eliminar registro de tiempo' })).toBeInTheDocument();
  });

it('displays EDT actual vs estimated hours synchronization and physical progress impact', async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce([]);
    render(
      <TaskTimeTrackingSection
        task={{
          ...task,
          estimated_hours: 10,
          actual_hours: 4.5,
          physical_progress_pct: 45,
        }}
        token="test-token"
      />,
    );

    expect(await screen.findByText(/Sincronización EDT:/i)).toBeInTheDocument();
    expect(screen.getByText('4.50h reales')).toBeInTheDocument();
    expect(screen.getByText(/10\.00h estimadas/i)).toBeInTheDocument();
  });

  it('calculates earned effort, labor efficiency, remaining effort, forecast and billable breakdown', async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce([
      { ...log, id: 'billable', hours: 3, is_billable: true },
      { ...log, id: 'non-billable', hours: 2, is_billable: false },
    ]);
    render(
      <TaskTimeTrackingSection
        task={{
          ...task,
          estimated_hours: 8,
          actual_hours: 1,
          physical_progress_pct: 50,
          progress_pct: 90,
        }}
        token="test-token"
      />,
    );

    expect(await screen.findByTestId('task-time-pmi-effort-diagnosis')).toBeInTheDocument();
    expect(screen.getByTestId('task-time-pmi-ev-hours')).toHaveTextContent('4.00h');
    expect(screen.getByTestId('task-time-pmi-lei')).toHaveTextContent('0.80');
    expect(screen.getByTestId('task-time-pmi-etc-hours')).toHaveTextContent('4.00h');
    expect(screen.getByTestId('task-time-pmi-eac-hours')).toHaveTextContent('9.00h');
    expect(screen.getByTestId('task-time-pmi-billable-hours')).toHaveTextContent('3.00h');
    expect(screen.getByTestId('task-time-pmi-non-billable-hours')).toHaveTextContent('2.00h');
    expect(screen.queryByTestId('task-time-pmi-over-effort-alert')).not.toBeInTheDocument();
  });

  it('uses completed status as the progress fallback and alerts when actual effort exceeds estimate', async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce([]);
    render(
      <TaskTimeTrackingSection
        task={{ ...task, status: 'completed', estimated_hours: 4, actual_hours: 5 }}
        token="test-token"
      />,
    );

    expect(await screen.findByTestId('task-time-pmi-effort-diagnosis')).toBeInTheDocument();
    expect(screen.getByTestId('task-time-pmi-ev-hours')).toHaveTextContent('4.00h');
    expect(screen.getByTestId('task-time-pmi-lei')).toHaveTextContent('0.80');
    expect(screen.getByTestId('task-time-pmi-etc-hours')).toHaveTextContent('0.00h');
    expect(screen.getByTestId('task-time-pmi-eac-hours')).toHaveTextContent('5.00h');
    expect(screen.getByTestId('task-time-pmi-over-effort-alert')).toHaveTextContent('Exceso de Esfuerzo EDT');
  });

  it('shows the effort diagnosis with an unavailable LEI when only actual hours are known', async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce([]);
    render(
      <TaskTimeTrackingSection task={{ ...task, actual_hours: 2 }} token="test-token" />,
    );

    expect(await screen.findByTestId('task-time-pmi-effort-diagnosis')).toBeInTheDocument();
    expect(screen.getByTestId('task-time-pmi-lei')).toHaveTextContent('—');
    expect(screen.getByTestId('task-time-pmi-ev-hours')).toHaveTextContent('0.00h');
    expect(screen.getByTestId('task-time-pmi-eac-hours')).toHaveTextContent('2.00h');
  });
});
