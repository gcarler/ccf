import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import ProjectsShell, { getPmiDomainLabel, type BreadcrumbOption } from './ProjectsShell';

vi.mock('@/components/WorkspaceToolbar', () => ({
  default: ({
    breadcrumbs,
    rightActions,
  }: {
    breadcrumbs: BreadcrumbOption[];
    rightActions?: React.ReactNode;
  }) => (
    <header data-testid="mock-workspace-toolbar">
      <nav aria-label="Breadcrumbs">
        {breadcrumbs.map((b) => (
          <span key={b.label}>{b.label}</span>
        ))}
      </nav>
      <div>{rightActions}</div>
    </header>
  ),
}));

vi.mock('@/components/WorkspaceLayout', () => ({
  UserMenuDropdown: ({ onOpenAppearance }: { onOpenAppearance: () => void }) => (
    <button type="button" onClick={onOpenAppearance} data-testid="mock-user-menu">
      Perfil
    </button>
  ),
}));

vi.mock('@/components/ui/ThemeToggle', () => ({
  default: ({ onOpenAppearance }: { onOpenAppearance: () => void }) => (
    <button type="button" onClick={onOpenAppearance} data-testid="mock-theme-toggle">
      Personalizar Apariencia
    </button>
  ),
}));

vi.mock('@/components/ui/AppearanceDrawer', () => ({
  default: ({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) =>
    isOpen ? (
      <div data-testid="mock-appearance-drawer">
        <span>Drawer de Apariencia Abierto</span>
        <button type="button" onClick={onClose}>
          Cerrar Apariencia
        </button>
      </div>
    ) : null,
}));

describe('ProjectsShell', () => {
  it('calcula las etiquetas de dominio PMI según viewType mediante getPmiDomainLabel', () => {
    expect(getPmiDomainLabel('gantt')).toBe('Ruta Critica y Cronograma');
    expect(getPmiDomainLabel('board')).toBe('Control de Flujo WIP');
    expect(getPmiDomainLabel('kanban')).toBe('Control de Flujo WIP');
    expect(getPmiDomainLabel('table')).toBe('Desglose de Paquetes WBS');
    expect(getPmiDomainLabel('list')).toBe('Desglose de Paquetes WBS');
    expect(getPmiDomainLabel('workflow')).toBe('Desglose de Paquetes WBS');
    expect(getPmiDomainLabel('wiki')).toBe('Activos de Conocimiento OPA');
    expect(getPmiDomainLabel('dashboard')).toBe('Monitoreo Ejecutivo EVM');
    expect(getPmiDomainLabel(undefined)).toBe('Monitoreo Ejecutivo EVM');
  });

  it('renderiza la píldora de gobernanza PMI dinámica según viewType', () => {
    const { rerender } = render(
      <ProjectsShell
        breadcrumbs={[{ label: 'Proyectos', href: '/plataforma/proyectos' }, { label: 'Portafolio' }]}
        viewType="gantt"
      >
        <div>Vista Gantt Activa</div>
      </ProjectsShell>
    );

    expect(screen.getByTestId('projects-shell-pmi-domain')).toHaveTextContent(
      'Ruta Critica y Cronograma'
    );

    rerender(
      <ProjectsShell
        breadcrumbs={[{ label: 'Proyectos', href: '/plataforma/proyectos' }]}
        viewType="board"
      >
        <div>Vista Kanban Activa</div>
      </ProjectsShell>
    );
    expect(screen.getByTestId('projects-shell-pmi-domain')).toHaveTextContent(
      'Control de Flujo WIP'
    );

    rerender(
      <ProjectsShell
        breadcrumbs={[{ label: 'Proyectos', href: '/plataforma/proyectos' }]}
        viewType="wiki"
      >
        <div>Vista Wiki Activa</div>
      </ProjectsShell>
    );
    expect(screen.getByTestId('projects-shell-pmi-domain')).toHaveTextContent(
      'Activos de Conocimiento OPA'
    );
  });

  it('renderiza breadcrumbs, children dentro de la sección accesible y abre AppearanceDrawer desde ThemeToggle', () => {
    render(
      <ProjectsShell
        breadcrumbs={[
          { label: 'Proyectos', href: '/plataforma/proyectos' },
          { label: 'Torre Faro' },
        ]}
        viewType="table"
        rightActions={<button type="button">Nueva Tarea</button>}
      >
        <div data-testid="shell-child-content">Tabla WBS del Proyecto</div>
      </ProjectsShell>
    );

    expect(screen.getByText('Proyectos')).toBeInTheDocument();
    expect(screen.getByText('Torre Faro')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Nueva Tarea' })).toBeInTheDocument();

    const contentSection = screen.getByRole('region', { name: 'Contenido de proyectos' });
    expect(contentSection).toContainElement(screen.getByTestId('shell-child-content'));

    expect(screen.queryByTestId('mock-appearance-drawer')).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId('mock-theme-toggle'));
    expect(screen.getByTestId('mock-appearance-drawer')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Cerrar Apariencia' }));
    expect(screen.queryByTestId('mock-appearance-drawer')).not.toBeInTheDocument();
  });
});
