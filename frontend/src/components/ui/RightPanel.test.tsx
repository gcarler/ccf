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
});
