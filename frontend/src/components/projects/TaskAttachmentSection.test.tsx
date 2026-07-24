import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import TaskAttachmentSection from './TaskAttachmentSection';
import type { ProjectTaskRecord } from '@/types/projects';

vi.mock('@/lib/http', () => ({
  apiFetch: vi.fn().mockResolvedValue([]),
}));

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({ token: 'test-token', user: null, loading: false, isAuthenticated: true }),
}));

const taskWithAttachments: ProjectTaskRecord = {
  id: 't1',
  project_id: 'p1',
  title: 'Test task',
  status: 'todo',
  priority: 'medium',
  attachments: [
    { id: 'att1', task_id: 't1', filename: 'design.pdf', file_url: 'https://example.com/design.pdf', file_size: 2048 },
    { id: 'att2', task_id: 't1', filename: 'notes.txt', file_url: 'https://example.com/notes.txt', file_size: 512 },
  ],
};

const taskEmpty: ProjectTaskRecord = {
  id: 't2',
  project_id: 'p1',
  title: 'Empty task',
  status: 'todo',
  priority: 'medium',
  attachments: [],
};

describe('TaskAttachmentSection', () => {
  it('renders attachments with filenames', () => {
    render(
      <TaskAttachmentSection
        task={taskWithAttachments}
        uploading={false}
        deletingAttachmentId={null}
        onUpload={vi.fn()}
        onDelete={vi.fn()}
        onUploadingChange={vi.fn()}
      />
    );
    expect(screen.getByText('design.pdf')).toBeInTheDocument();
    expect(screen.getByText('notes.txt')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('renders empty state when no attachments', () => {
    render(
      <TaskAttachmentSection
        task={taskEmpty}
        uploading={false}
        deletingAttachmentId={null}
        onUpload={vi.fn()}
        onDelete={vi.fn()}
        onUploadingChange={vi.fn()}
      />
    );
    expect(screen.getByText('Sin archivos adjuntos aun.')).toBeInTheDocument();
  });
});
