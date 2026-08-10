import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { RoleSelect } from './RoleSelect';

const OPTIONS = [
  { value: 'lider', label: 'Lider' },
  { value: 'ujier', label: 'Ujier' },
  { value: 'maestro', label: 'Maestro' },
];

function makeProps(over: Partial<React.ComponentProps<typeof RoleSelect>> = {}): React.ComponentProps<typeof RoleSelect> {
  return { value: 'lider', options: OPTIONS, colorClass: 'bg-info', onChange: vi.fn(), ...over };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('RoleSelect', () => {
  describe('render y ARIA', () => {
    it('renderiza el trigger combobox con el label del valor actual', () => {
      render(<RoleSelect {...makeProps()} />);
      const trigger = screen.getByRole('combobox');
      expect(trigger).toHaveTextContent('Lider');
    });

    it('el trigger tiene aria-expanded=false cuando cerrado', () => {
      render(<RoleSelect {...makeProps()} />);
      expect(screen.getByRole('combobox')).toHaveAttribute('aria-expanded', 'false');
    });

    it('al abrir, aria-expanded=true, aria-controls apunta al listbox y aparece role=listbox', () => {
      render(<RoleSelect {...makeProps()} />);
      const trigger = screen.getByRole('combobox');
      fireEvent.click(trigger);
      expect(trigger).toHaveAttribute('aria-expanded', 'true');
      const listboxId = trigger.getAttribute('aria-controls')!;
      expect(listboxId).toBeTruthy();
      expect(document.getElementById(listboxId)).not.toBeNull();
      expect(screen.getByRole('listbox')).toBeInTheDocument();
    });

    it('cada opcion tiene role=option y aria-selected solo en la actual', () => {
      render(<RoleSelect {...makeProps()} />);
      fireEvent.click(screen.getByRole('combobox'));
      const opts = screen.getAllByRole('option');
      expect(opts).toHaveLength(3);
      expect(opts[0]).toHaveAttribute('aria-selected', 'true');
      expect(opts[1]).toHaveAttribute('aria-selected', 'false');
    });

    it('aria-activedescendant cambia con ArrowDown/ArrowUp', () => {
      render(<RoleSelect {...makeProps()} />);
      const trigger = screen.getByRole('combobox');
      fireEvent.click(trigger);
      // activa índice 0 al abrir (match value=lider), ArrowDown → 1
      fireEvent.keyDown(trigger, { key: 'ArrowDown' });
      expect(trigger).toHaveAttribute('aria-activedescendant', expect.stringContaining('-option-1'));
      fireEvent.keyDown(trigger, { key: 'ArrowDown' });
      expect(trigger).toHaveAttribute('aria-activedescendant', expect.stringContaining('-option-2'));
      fireEvent.keyDown(trigger, { key: 'ArrowUp' });
      expect(trigger).toHaveAttribute('aria-activedescendant', expect.stringContaining('-option-1'));
    });
  });

  describe('navegación por teclado', () => {
    it('ArrowDown abre el listbox estando cerrado', () => {
      render(<RoleSelect {...makeProps()} />);
      const trigger = screen.getByRole('combobox');
      fireEvent.keyDown(trigger, { key: 'ArrowDown' });
      expect(screen.getByRole('listbox')).toBeInTheDocument();
    });

    it('Escape cierra el listbox', () => {
      render(<RoleSelect {...makeProps()} />);
      const trigger = screen.getByRole('combobox');
      fireEvent.click(trigger);
      expect(screen.getByRole('listbox')).toBeInTheDocument();
      fireEvent.keyDown(trigger, { key: 'Escape' });
      expect(screen.queryByRole('listbox')).toBeNull();
    });

    it('Enter cuando cerrado abre el listbox', () => {
      render(<RoleSelect {...makeProps()} />);
      const trigger = screen.getByRole('combobox');
      fireEvent.keyDown(trigger, { key: 'Enter' });
      expect(screen.getByRole('listbox')).toBeInTheDocument();
    });

    it('Enter con listbox abierto dispara onChange con la opción activa', () => {
      const props = makeProps();
      render(<RoleSelect {...props} />);
      const trigger = screen.getByRole('combobox');
      fireEvent.click(trigger);
      fireEvent.keyDown(trigger, { key: 'ArrowDown' }); // activo → índice 1 (Ujier)
      fireEvent.keyDown(trigger, { key: 'Enter' });
      expect(props.onChange).toHaveBeenCalledWith('ujier');
    });

    it('Space alterna apertura cuando cerrado', () => {
      render(<RoleSelect {...makeProps()} />);
      const trigger = screen.getByRole('combobox');
      fireEvent.keyDown(trigger, { key: ' ' });
      expect(screen.getByRole('listbox')).toBeInTheDocument();
    });

    it('Home lleva activeIndex a 0', () => {
      render(<RoleSelect {...makeProps()} />);
      const trigger = screen.getByRole('combobox');
      fireEvent.click(trigger);
      fireEvent.keyDown(trigger, { key: 'ArrowDown' });
      fireEvent.keyDown(trigger, { key: 'ArrowDown' }); // índice 2
      fireEvent.keyDown(trigger, { key: 'Home' });
      expect(trigger).toHaveAttribute('aria-activedescendant', expect.stringContaining('-option-0'));
    });

    it('End lleva activeIndex al último', () => {
      render(<RoleSelect {...makeProps()} />);
      const trigger = screen.getByRole('combobox');
      fireEvent.click(trigger);
      fireEvent.keyDown(trigger, { key: 'End' });
      expect(trigger).toHaveAttribute('aria-activedescendant', expect.stringContaining('-option-2'));
    });

    it('ArrowUp no desborda por debajo de 0', () => {
      render(<RoleSelect {...makeProps()} />);
      const trigger = screen.getByRole('combobox');
      fireEvent.click(trigger);
      fireEvent.keyDown(trigger, { key: 'ArrowUp' });
      expect(trigger).toHaveAttribute('aria-activedescendant', expect.stringContaining('-option-0'));
    });

    it('ArrowDown no desborda por encima del último', () => {
      render(<RoleSelect {...makeProps()} />);
      const trigger = screen.getByRole('combobox');
      fireEvent.click(trigger);
      fireEvent.keyDown(trigger, { key: 'ArrowDown' });
      fireEvent.keyDown(trigger, { key: 'ArrowDown' });
      fireEvent.keyDown(trigger, { key: 'ArrowDown' }); // intenta pasarse del 2
      expect(trigger).toHaveAttribute('aria-activedescendant', expect.stringContaining('-option-2'));
    });
  });

  describe('clic e interacción con mouse', () => {
    it('click en trigger alterna apertura', () => {
      render(<RoleSelect {...makeProps()} />);
      const trigger = screen.getByRole('combobox');
      fireEvent.click(trigger);
      expect(screen.getByRole('listbox')).toBeInTheDocument();
      fireEvent.click(trigger);
      expect(screen.queryByRole('listbox')).toBeNull();
    });

    it('click en una opción dispara onChange y cierra', () => {
      const props = makeProps();
      render(<RoleSelect {...props} />);
      fireEvent.click(screen.getByRole('combobox'));
      fireEvent.click(screen.getByText('Maestro'));
      expect(props.onChange).toHaveBeenCalledWith('maestro');
      expect(screen.queryByRole('listbox')).toBeNull();
    });
  });
});
