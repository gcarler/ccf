import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

vi.mock('@/context/AuthContext', () => ({
    useAuth: () => ({ user: { id: 'u1', role: 'admin' }, hasPermission: () => true, loading: false }),
}));
import ProjectsBoardView from './ProjectsBoardView';
import { createMockProject } from '@/test-utils/factories';

const projects = [
    createMockProject({
        id: 'p1',
        title: 'Proyecto activo',
        description: 'En marcha',
        status: 'active',
        color: '#2563eb',
        owner_id: 'u1',
        created_at: '2025-06-15T10:00:00Z',
        tasks: [],
    }),
    createMockProject({
        id: 'p2',
        title: 'Proyecto completado',
        description: 'Finalizado',
        status: 'completed',
        color: '#16a34a',
        owner_id: 'u2',
        created_at: '2025-06-16T10:00:00Z',
        tasks: [],
    }),
];

describe('ProjectsBoardView', () => {
    it('groups projects by status into columns', () => {
        render(<ProjectsBoardView projects={projects} onUpdate={vi.fn()} onDelete={vi.fn()} />);
        expect(screen.getByText('active')).toBeInTheDocument();
        expect(screen.getByText('completed')).toBeInTheDocument();
        expect(screen.getByText('Proyecto activo')).toBeInTheDocument();
        expect(screen.getByText('Proyecto completado')).toBeInTheDocument();
    });

    it('shows empty column placeholder when no projects in a required column', () => {
        render(<ProjectsBoardView projects={[]} onUpdate={vi.fn()} onDelete={vi.fn()} />);
        expect(screen.getAllByText('Vacío').length).toBeGreaterThanOrEqual(1);
    });
});
