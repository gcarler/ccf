import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({ token: 'test-token' }),
}));

vi.mock('@/components/ui/RightPanel', () => ({
  RightPanel: ({ open, children }: { open: boolean; children: React.ReactNode }) =>
    open ? <div>{children}</div> : null,
}));

vi.mock('next/dynamic', () => ({
  default: () => {
    const MockWhiteboardEditor = ({
      header,
    }: {
      header: (args: {
        title: string;
        saveStatus: 'saved';
        saveNow: () => void;
        isDirty: boolean;
        hasConflict: boolean;
      }) => React.ReactNode;
    }) => (
      <div data-testid="whiteboard-editor-mock">
        {header({
          title: 'Pizarra WBS',
          saveStatus: 'saved',
          saveNow: vi.fn(),
          isDirty: false,
          hasConflict: false,
        })}
      </div>
    );
    return MockWhiteboardEditor;
  },
}));

import ProjectWhiteboard from './ProjectWhiteboard';

describe('ProjectWhiteboard', () => {
  it('returns null when isOpen is false', () => {
    render(<ProjectWhiteboard project_id="proj-1" isOpen={false} onClose={vi.fn()} />);
    expect(screen.queryByTestId('project-whiteboard-portal')).not.toBeInTheDocument();
  });

  it('renders portal with ProjectWhiteboardHeader when isOpen is true and triggers onClose', () => {
    const onClose = vi.fn();
    render(<ProjectWhiteboard project_id="proj-1" isOpen={true} onClose={onClose} />);

    expect(screen.getByTestId('project-whiteboard-portal')).toBeInTheDocument();
    expect(screen.getByText('Pizarra WBS')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /cerrar/i }));
    expect(onClose).toHaveBeenCalledOnce();
  });
});
