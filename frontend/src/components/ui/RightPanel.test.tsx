import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { axe } from 'jest-axe';
import RightPanel from './RightPanel';
import { SidebarLayerProvider } from '@/context/SidebarLayerContext';

function renderWithProvider(ui: React.ReactElement) {
  return render(<SidebarLayerProvider>{ui}</SidebarLayerProvider>);
}

describe('RightPanel', () => {
  it('does not render content when closed', () => {
    renderWithProvider(
      <RightPanel open={false} onClose={() => {}}>
        <div data-testid="content">Contenido</div>
      </RightPanel>
    );
    expect(screen.queryByTestId('content')).not.toBeInTheDocument();
    expect(screen.queryByRole('complementary')).not.toBeInTheDocument();
  });

  it('renders title and children when open', () => {
    renderWithProvider(
      <RightPanel open title="Panel de prueba">
        <div data-testid="content">Contenido del panel</div>
      </RightPanel>
    );
    expect(screen.getByText('Panel de prueba')).toBeInTheDocument();
    expect(screen.getByTestId('content')).toBeInTheDocument();
    expect(screen.getByText('Panel de prueba')).toHaveClass('text-[hsl(var(--foreground))]');
  });

  it('calls onClose when the close button is clicked', () => {
    const handleClose = vi.fn();
    renderWithProvider(
      <RightPanel open onClose={handleClose}>
        <div>Contenido</div>
      </RightPanel>
    );
    fireEvent.click(screen.getByLabelText('Cerrar panel'));
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it('supports trigger rendering in controlled mode', () => {
    const Trigger = <button data-testid="trigger">Abrir</button>;
    renderWithProvider(
      <RightPanel open={false} onClose={() => {}} showTrigger trigger={Trigger}>
        <div>Contenido</div>
      </RightPanel>
    );
    expect(screen.getByTestId('trigger')).toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = renderWithProvider(
      <RightPanel open title="Panel accesible">
        <p>Contenido</p>
      </RightPanel>
    );
    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });
  it('embeds tool content without creating a second overlay or focus trap', () => {
    renderWithProvider(
      <RightPanel open title="Centro de gestión">
        <RightPanel embedded open title="Diccionario"><button>Editar paquete</button></RightPanel>
      </RightPanel>
    );
    expect(screen.getAllByRole('dialog')).toHaveLength(1);
    expect(screen.getByRole('region', { name: 'Diccionario' })).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: 'Cerrar panel' })).toHaveLength(1);
  });

  it('renders a manual resize handle when resizable or resizeStorageKey is provided', () => {
    window.innerWidth = 1200;
    renderWithProvider(
      <RightPanel open resizable title="Panel ajustable">
        <p>Contenido ajustable</p>
      </RightPanel>
    );
    expect(screen.getByRole('separator', { name: 'Ajustar ancho del panel' })).toBeInTheDocument();
  });

  it('renders a manual resize handle with custom storage key', () => {
    window.innerWidth = 1200;
    renderWithProvider(
      <RightPanel open resizeStorageKey="workspace:project_tools_width" resizeDefaultWidth={960} title="Herramientas">
        <p>Herramientas de gestión</p>
      </RightPanel>
    );
    expect(screen.getByRole('separator', { name: 'Ajustar ancho del panel' })).toBeInTheDocument();
  });

  describe('hasBackdrop=false (paneles no modales / coexistencia)', () => {
    it('no renderiza backdrop (sin difuminado ni bloqueo de clics externos)', () => {
      const { container } = renderWithProvider(
        <RightPanel open hasBackdrop={false} title="Herramienta no modal">
          <p>Contenido libre</p>
        </RightPanel>
      );
      expect(container.querySelector('[class*="backdrop-blur"]')).toBeNull();
    });

    it('omite aria-modal en el panel', () => {
      renderWithProvider(
        <RightPanel open hasBackdrop={false} title="Herramienta no modal">
          <p>Contenido libre</p>
        </RightPanel>
      );
      expect(screen.getByRole('dialog')).not.toHaveAttribute('aria-modal');
    });

    it('mantiene aria-modal="true" cuando el backdrop está activo (default)', () => {
      renderWithProvider(
        <RightPanel open title="Drawer modal">
          <p>Contenido</p>
        </RightPanel>
      );
      expect(screen.getByRole('dialog')).toHaveAttribute('aria-modal', 'true');
    });

    it('desplaza el panel a la derecha según offsetRight', () => {
      renderWithProvider(
        <RightPanel open hasBackdrop={false} offsetRight={380} title="Panel desplazado">
          <p>Coexistencia</p>
        </RightPanel>
      );
      expect(screen.getByRole('dialog', { name: 'Panel desplazado' })).toHaveStyle({ right: '380px' });
    });

    it('aplica right: 0 cuando offsetRight === 0', () => {
      renderWithProvider(
        <RightPanel open hasBackdrop={false} offsetRight={0} title="Panel pegado">
          <p>Coexistencia</p>
        </RightPanel>
      );
      expect(screen.getByRole('dialog', { name: 'Panel pegado' })).toHaveStyle({ right: '0px' });
    });
  });
});
