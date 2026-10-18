import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { ProjectTaskRecord } from '@/types/projects';

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({ token: 'test-token', loading: false }),
}));

vi.mock('@/lib/http', () => ({
  apiFetch: vi.fn().mockResolvedValue([]),
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock('./TaskDetailHeader', () => ({
  default: () => <div data-testid="task-detail-header-mock" />,
}));
vi.mock('./TaskMetaFields', () => ({
  default: () => <div data-testid="task-meta-fields-mock" />,
}));
vi.mock('./TaskDimensionsSection', () => ({
  default: () => <div data-testid="task-dimensions-mock" />,
}));
vi.mock('./TaskAttachmentSection', () => ({
  default: () => <div data-testid="task-attachment-mock" />,
}));
vi.mock('./TaskSupplySection', () => ({
  default: () => <div data-testid="task-supply-mock" />,
}));
vi.mock('./TaskTimeTrackingSection', () => ({
  default: () => <div data-testid="task-time-mock" />,
}));
vi.mock('./TaskActivitySection', () => ({
  default: () => <div data-testid="task-activity-mock" />,
  toggleActivity: vi.fn(),
  addChild: vi.fn(),
  updateTitle: vi.fn(),
}));
vi.mock('./TaskCommentSection', () => ({
  default: () => <div data-testid="task-comment-mock" />,
}));
vi.mock('@/components/ConfirmActionDrawer', () => ({
  default: () => null,
}));

import TaskDetailPanel from './TaskDetailPanel';

const baseTask: ProjectTaskRecord = {
  id: 'task-1',
  project_id: 'proj-1',
  title: 'Paquete WBS 1.2',
  description: '',
  status: 'in_progress',
  priority: 'high',
  due_date: null,
  assignee_id: null,
  subtasks: [
    { id: 'sub-1', project_id: 'proj-1', title: 'Sub 1', status: 'completed', priority: 'medium' },
    { id: 'sub-2', project_id: 'proj-1', title: 'Sub 2', status: 'todo', priority: 'medium' },
  ],
  supplies: [{ id: 'sup-1', task_id: 'task-1', item_name: 'Cable', quantity: 2, unit_cost: 10, status: 'pending' }],
  attachments: [],
};

describe('TaskDetailPanel PMI §5.3.2 WBS Work Package Dictionary', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders WBS dictionary strip with EVMT credit, decomposition counts and incomplete readiness when missing fields', () => {
    render(<TaskDetailPanel task={baseTask} onClose={vi.fn()} />);

    const strip = screen.getByTestId('task-detail-pmi-wp-dictionary');
    expect(strip).toHaveTextContent('Diccionario WBS PMI §5.3.2');
    expect(strip).toHaveTextContent('50% EV (En Curso)');
    expect(strip).toHaveTextContent('2 sub-actividad(es) (1 completada(s))');
    expect(strip).toHaveTextContent('1 insumo(s) · 0 adjunto(s)');
    expect(screen.getByTestId('task-detail-pmi-wp-readiness')).toHaveTextContent(
      'Definición Incompleta',
    );
  });

  it('renders Definición Completa when description, due_date and assignee are defined, and appends PMI scope templates', () => {
    const completeTask: ProjectTaskRecord = {
      ...baseTask,
      id: 'task-2',
      status: 'completed',
      description: 'Alcance inicial',
      due_date: '2026-10-30',
      assignee_id: 'user-1',
    };

    render(<TaskDetailPanel task={completeTask} onClose={vi.fn()} />);

    expect(screen.getByTestId('task-detail-pmi-wp-dictionary')).toHaveTextContent(
      '100% EV (Aceptado)',
    );
    expect(screen.getByTestId('task-detail-pmi-wp-readiness')).toHaveTextContent(
      'Definición Completa',
    );

    fireEvent.click(screen.getByTestId('task-desc-tpl-deliverable'));
    const textarea = screen.getByPlaceholderText('Añade una descripción...');
    expect(textarea).toHaveValue(
      'Alcance inicial\n[Entregable]:  | [Criterio de Aceptación]: ',
    );
  });
});
