import { render, screen, fireEvent } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import CrmOperationalDataView from './CrmOperationalDataView';

describe('CrmOperationalDataView', () => {
  it('renders real records and opens the selected record', () => {
    const onSelect = vi.fn();
    render(
      <CrmOperationalDataView
        moduleName="Consejería"
        items={[{ id: 'c-1', title: 'Acompañamiento familiar', subtitle: 'Ana Pérez', meta: 'Pendiente' }]}
        onSelect={onSelect}
      />,
    );

    expect(screen.getByText('Acompañamiento familiar')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Acompañamiento familiar/i }));
    expect(onSelect).toHaveBeenCalledWith({
      id: 'c-1',
      title: 'Acompañamiento familiar',
      subtitle: 'Ana Pérez',
      meta: 'Pendiente',
    });
  });

  it('shows an explicit empty state without simulated records', () => {
    render(<CrmOperationalDataView moduleName="Tareas" items={[]} />);
    expect(screen.getByText('No hay registros para mostrar.')).toBeInTheDocument();
    expect(screen.queryByText(/pendiente de datos/i)).not.toBeInTheDocument();
  });
});
