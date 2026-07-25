import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import ProjectsWikiView from './ProjectsWikiView';

vi.mock('@/components/ui/UniversalWikiView', () => ({
    default: ({ moduleName, storageKey }: { moduleName: string; storageKey: string }) => (
        <div data-testid="wiki">
            <h2>{moduleName}</h2>
            <span>{storageKey}</span>
        </div>
    ),
}));

describe('ProjectsWikiView', () => {
    it('renders the wiki view with module name and storage key', () => {
        render(<ProjectsWikiView />);
        expect(screen.getByText('Proyectos')).toBeInTheDocument();
        expect(screen.getByText('wiki_projects_portfolio')).toBeInTheDocument();
    });
});
