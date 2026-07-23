import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { axe } from 'jest-axe';
import { Plus } from 'lucide-react';
import SplitDropdownButton from './SplitDropdownButton';

describe('SplitDropdownButton', () => {
  it('renders main label and icon', () => {
    render(<SplitDropdownButton onMainClick={() => {}} mainLabel="Nuevo" icon={Plus} />);
    expect(screen.getByText('Nuevo')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /nuevo/i })).toBeInTheDocument();
  });

  it('calls onMainClick when the main button is clicked', () => {
    const handleMainClick = vi.fn();
    render(<SplitDropdownButton onMainClick={handleMainClick} mainLabel="Crear" />);
    fireEvent.click(screen.getByRole('button', { name: /crear/i }));
    expect(handleMainClick).toHaveBeenCalledTimes(1);
  });

  it('opens and closes the dropdown when the chevron is clicked', async () => {
    render(<SplitDropdownButton onMainClick={() => {}} mainLabel="Nuevo" />);
    const chevron = screen.getByRole('button', { name: /mostrar opciones/i });
    fireEvent.click(chevron);
    expect(screen.getByText('Tarea')).toBeInTheDocument();
    expect(screen.getByText('Documento')).toBeInTheDocument();
    fireEvent.click(chevron);
    await waitFor(() => {
      expect(screen.queryByText('Tarea')).not.toBeInTheDocument();
    });
  });

  it('calls onOptionClick when an option is selected', () => {
    const handleOptionClick = vi.fn();
    render(<SplitDropdownButton onMainClick={() => {}} mainLabel="Nuevo" onOptionClick={handleOptionClick} />);
    fireEvent.click(screen.getByRole('button', { name: /mostrar opciones/i }));
    fireEvent.click(screen.getByText('Recordatorio'));
    expect(handleOptionClick).toHaveBeenCalledTimes(1);
    expect(handleOptionClick).toHaveBeenCalledWith('reminder');
  });

  it('calls custom onClick defined in the option', () => {
    const customClick = vi.fn();
    render(
      <SplitDropdownButton
        onMainClick={() => {}}
        mainLabel="Nuevo"
        options={[{ id: 'custom', label: 'Personalizado', onClick: customClick }]}
      />
    );
    fireEvent.click(screen.getByRole('button', { name: /mostrar opciones/i }));
    fireEvent.click(screen.getByText('Personalizado'));
    expect(customClick).toHaveBeenCalledTimes(1);
  });

  it('closes the dropdown when clicking outside', async () => {
    render(
      <div>
        <SplitDropdownButton onMainClick={() => {}} mainLabel="Nuevo" />
        <div data-testid="outside">Fuera</div>
      </div>
    );
    fireEvent.click(screen.getByRole('button', { name: /mostrar opciones/i }));
    expect(screen.getByText('Tarea')).toBeInTheDocument();
    fireEvent.mouseDown(screen.getByTestId('outside'));
    await waitFor(() => {
      expect(screen.queryByText('Tarea')).not.toBeInTheDocument();
    });
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<SplitDropdownButton onMainClick={() => {}} mainLabel="Nuevo" />);
    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });
});
