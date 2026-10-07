import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import ProjectsListView from './ProjectsListView';
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
        status: 'planning',
        color: '#8b5cf6',
        owner_id: 'u2',
        created_at: '2025-06-16T10:00:00Z',
        tasks: [],
    }),
];

describe('ProjectsListView', () => {
    it('provides an explicit accessible detail action without making inline controls navigate', () => {
        pushMock.mockClear();
        render(<ProjectsListView projects={projects} onUpdate={vi.fn()} />);

        fireEvent.click(screen.getByText('Campamento Juventud'));
        expect(pushMock).not.toHaveBeenCalled();

        fireEvent.click(screen.getByRole('button', { name: 'Abrir proyecto Campamento Juventud' }));
        expect(pushMock).toHaveBeenCalledWith('/plataforma/projects/p1?view=list');
    });

    it('renders project titles and descriptions', () => {
        render(<ProjectsListView projects={projects} onUpdate={vi.fn()} />);
        expect(screen.getByText('Campamento Juventud')).toBeInTheDocument();
        expect(screen.getByText('Organización del campamento')).toBeInTheDocument();
        expect(screen.getByText('Retiro Pastoral')).toBeInTheDocument();
    });

    it('calls onUpdate when a project title is edited', () => {
        pushMock.mockClear();
        const onUpdate = vi.fn();
        render(<ProjectsListView projects={projects} onUpdate={onUpdate} />);
        const title = screen.getByText('Campamento Juventud');
        fireEvent.click(title);
        const input = screen.getByDisplayValue('Campamento Juventud');
        fireEvent.change(input, { target: { value: 'Campamento Juventud 2026' } });
        fireEvent.blur(input);
        expect(onUpdate).toHaveBeenCalledWith('p1', { title: 'Campamento Juventud 2026' });
        expect(pushMock).not.toHaveBeenCalled();
    });
});
