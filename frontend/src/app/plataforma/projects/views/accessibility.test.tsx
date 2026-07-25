import React from 'react';
import { render } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { axe } from 'jest-axe';

vi.mock('@/context/AuthContext', () => ({
    useAuth: () => ({ user: { id: 'u1', role: 'admin' }, hasPermission: () => true, loading: false }),
}));
import ProjectsGridView from './ProjectsGridView';
import ProjectsListView from './ProjectsListView';
import ProjectsBoardView from './ProjectsBoardView';
import type { ProjectRecord } from '@/types/projects';

const projects: ProjectRecord[] = [
    {
        id: 'p1',
        title: 'Campamento Juventud',
        description: 'Organización del campamento',
        status: 'active',
        color: '#2563eb',
        owner_id: 'u1',
        created_at: '2025-06-15T10:00:00Z',
        tasks: [],
    } as ProjectRecord,
];

describe('Projects views accessibility', () => {
    it('ProjectsGridView has no critical a11y violations', async () => {
        const { container } = render(<ProjectsGridView projects={projects} onUpdate={() => {}} />);
        const results = await axe(container);
        expect(results.violations).toEqual([]);
    });

    it('ProjectsListView has no critical a11y violations', async () => {
        const { container } = render(<ProjectsListView projects={projects} onUpdate={() => {}} />);
        const results = await axe(container);
        expect(results.violations).toEqual([]);
    });

    it('ProjectsBoardView has no critical a11y violations', async () => {
        const { container } = render(<ProjectsBoardView projects={projects} onUpdate={() => {}} />);
        const results = await axe(container);
        expect(results.violations).toEqual([]);
    });
});
