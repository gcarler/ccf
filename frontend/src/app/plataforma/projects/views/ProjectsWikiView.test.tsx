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

    it('renders PMI §4.4 OPA central repository banner and taxonomy tags', () => {
        render(<ProjectsWikiView />);
        expect(screen.getByTestId('projects-wiki-pmi-opa-banner')).toHaveTextContent(
            'Repositorio Central de Activos de Procesos de la Organización (OPA) · PMI §4.4'
        );
        const taxonomy = screen.getByTestId('projects-wiki-opa-taxonomy');
        expect(taxonomy).toHaveTextContent('Políticas, Estándares y Plantillas PMO');
        expect(taxonomy).toHaveTextContent('Registro Histórico de Lecciones Aprendidas');
        expect(taxonomy).toHaveTextContent('Criterios de Salida Stage-Gate y DoD');
    });
});

