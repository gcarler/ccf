import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import ProjectsTableView from './ProjectsTableView';
import { createMockProject } from '@/test-utils/factories';

const { pushMock } = vi.hoisted(() => ({ pushMock: vi.fn() }));

vi.mock('next/navigation', () => ({
    useRouter: () => ({ push: pushMock }),
}));

const projects = [
    createMockProject({
        id: 'p1',
        title: 'Campamento Juventud',
        description: 'Organización del campamento',
        status: 'active',
        color: '#2563eb',
        owner_id: 'u1',
        created_at: '2025-06-15T10:00:00Z',
        tasks: [],
    }),
    createMockProject({
        id: 'p2',
        title: 'Retiro Pastoral',
        description: 'Planificación del retiro',
        status: 'completed',
        color: '#8b5cf6',
        owner_id: 'u2',
        created_at: '2025-06-16T10:00:00Z',
        tasks: [],
    }),
];

describe('ProjectsTableView', () => {
    it('keeps inline editing separate from an accessible detail action', () => {
        pushMock.mockClear();
        render(<ProjectsTableView projects={projects} onUpdate={vi.fn()} />);

        fireEvent.click(screen.getByText('Campamento Juventud'));
        expect(pushMock).not.toHaveBeenCalled();

        fireEvent.click(screen.getByRole('button', { name: 'Abrir proyecto Campamento Juventud' }));
        expect(pushMock).toHaveBeenCalledWith('/plataforma/projects/p1?view=list');
    });

    it('renders project titles and status pickers', () => {
        render(<ProjectsTableView projects={projects} onUpdate={vi.fn()} />);
        expect(screen.getByText('Campamento Juventud')).toBeInTheDocument();
        expect(screen.getByText('Retiro Pastoral')).toBeInTheDocument();
    });

    it('calls onUpdate when title is edited', () => {
        pushMock.mockClear();
        const onUpdate = vi.fn();
        render(<ProjectsTableView projects={projects} onUpdate={onUpdate} />);
        const title = screen.getByText('Campamento Juventud');
        fireEvent.click(title);
        const input = screen.getByDisplayValue('Campamento Juventud');
        fireEvent.change(input, { target: { value: 'Campamento 2026' } });
        fireEvent.blur(input);
        expect(onUpdate).toHaveBeenCalledWith('p1', { title: 'Campamento 2026' });
        expect(pushMock).not.toHaveBeenCalled();
    });
});
