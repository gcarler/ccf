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
  it('keeps a resizable tool within the remaining desktop space beside context', () => {
    const previousWidth = window.innerWidth;
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 1280 });
    try {
      renderWithProvider(<RightPanel open resizable offsetRight={380} title="Adjacent tool"><p>Content</p></RightPanel>);
      const panel = screen.getByRole('dialog', { name: 'Adjacent tool' });
      expect(panel).toHaveStyle({ right: '380px', width: '852px' });
    } finally {
      Object.defineProperty(window, 'innerWidth', { configurable: true, value: previousWidth });
    }
  });

  it('uses the entire mobile viewport when an adjacent context offset is configured', () => {
    const previousWidth = window.innerWidth;
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 390 });
    try {
      renderWithProvider(<RightPanel open resizable offsetRight={380} title="Mobile tool"><p>Content</p></RightPanel>);
      const panel = screen.getByRole('dialog', { name: 'Mobile tool' });
      expect(panel).toHaveStyle({ right: '0px', width: '100%' });
    } finally {
      Object.defineProperty(window, 'innerWidth', { configurable: true, value: previousWidth });
    }
  });

  it('restores the invoker when a nonmodal panel closes from its own controls', () => {
    function Example() {
      const [open, setOpen] = React.useState(false);
      return <><button onClick={() => setOpen(true)}>Open tool</button><RightPanel open={open} hasBackdrop={false} onClose={() => setOpen(false)} title="Nonmodal tool"><button>Inner control</button></RightPanel></>;
    }
    renderWithProvider(<Example />);
    const trigger = screen.getByRole('button', { name: 'Open tool' });
    trigger.focus();
    fireEvent.click(trigger);
    screen.getByRole('button', { name: 'Cerrar panel' }).focus();
    fireEvent.click(screen.getByRole('button', { name: 'Cerrar panel' }));
    expect(trigger).toHaveFocus();
  });

  it('does not steal background focus when a nonmodal tool is closed externally', () => {
    function Example() {
      const [open, setOpen] = React.useState(false);
      return <><button onClick={() => setOpen(true)}>Open tool</button><button onClick={() => setOpen(false)}>Close from workspace</button><RightPanel open={open} hasBackdrop={false} onClose={() => setOpen(false)} title="Nonmodal tool"><button>Inner control</button></RightPanel></>;
    }
    renderWithProvider(<Example />);
    screen.getByRole('button', { name: 'Open tool' }).focus();
    fireEvent.click(screen.getByRole('button', { name: 'Open tool' }));
    const background = screen.getByRole('button', { name: 'Close from workspace' });
    background.focus();
    fireEvent.click(background);
    expect(background).toHaveFocus();
  });

});
