import React from 'react';
import { describe, it, expect, vi, beforeEach, type Mock } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import EventCardViews from './EventCardViews';
import type { EventDashboardStat, MinistryEvent } from '@/app/plataforma/evangelism/types';

function makeEvent(over: Partial<MinistryEvent> = {}): MinistryEvent {
  return {
    id: 'ev-1',
    name: 'Servicio Dominical',
    description: 'Servicio principal',
    event_type: 'PERMANENT',
    target_role_ids: [],
    target_persona_ids: [],
    ...over,
  };
}

const STAT: EventDashboardStat = { event_id: 'ev-1', latest_session: null, attended: 5, expected: 10, rate: 50 };

function makeProps(over: Partial<React.ComponentProps<typeof EventCardViews>> = {}) {
  return {
    viewType: 'grid' as const,
    events: [makeEvent()],
    onOpenEvent: vi.fn() as unknown as Mock,
    getTargetRoleLabel: vi.fn(() => 'Toda la iglesia'),
    getEventAttendanceStat: vi.fn(() => STAT),
    getVisualDate: vi.fn(() => '2026-01-01'),
    eventTypeLabel: { PERMANENT: 'Semanal' },
    eventTypeColor: { PERMANENT: 'badge-info' },
    onOpenQr: vi.fn(),
    onOpenAttendance: vi.fn(),
    menuOpenId: null,
    onMenuToggle: vi.fn(),
    onEdit: vi.fn(),
    onDelete: vi.fn(),
    ...over,
  } as React.ComponentProps<typeof EventCardViews> & { onOpenEvent: Mock };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('EventCardViews', () => {
  describe('grid view', () => {
    it('renderiza tarjeta con nombre, tipo y métricas de asistencia', () => {
      render(<EventCardViews {...makeProps()} />);
      expect(screen.getByText('Servicio Dominical')).toBeInTheDocument();
      expect(screen.getByText('Semanal')).toBeInTheDocument();
      expect(screen.getByText(/5/)).toBeInTheDocument();
    });

    it('muestra mensaje vacío cuando no hay eventos', () => {
      render(<EventCardViews {...makeProps({ events: [] })} />);
      expect(screen.getByText('No hay eventos registrados')).toBeInTheDocument();
    });

    it('onOpenEvent se dispara al click en la tarjeta y al Enter', () => {
      const props = makeProps();
      render(<EventCardViews {...props} />);
      const card = screen.getByText('Servicio Dominical').closest('div[role="link"]')!;
      fireEvent.click(card);
      expect(props.onOpenEvent).toHaveBeenCalledWith('ev-1');
      // reset + keyboard
      props.onOpenEvent.mockClear();
      fireEvent.keyDown(card, { key: 'Enter', preventDefault: () => {} });
      expect(props.onOpenEvent).toHaveBeenCalledWith('ev-1');
    });

    it('los botones QR / Asistencia invocan callbacks y detienen propagación', () => {
      const props = makeProps();
      render(<EventCardViews {...props} />);
      fireEvent.click(screen.getByTitle('Generar QR'));
      expect(props.onOpenQr).toHaveBeenCalledWith(expect.objectContaining({ id: 'ev-1' }));
      fireEvent.click(screen.getByText('Panel de Asistencia'));
      expect(props.onOpenAttendance).toHaveBeenCalledWith(expect.objectContaining({ id: 'ev-1' }));
      // La tarjeta no debe abrirse (stopPropagation)
      expect(props.onOpenEvent).not.toHaveBeenCalled();
    });

    it('toggle del menú contextual invoca onMenuToggle (botón MoreVertical)', () => {
      const props = makeProps();
      render(<EventCardViews {...props} />);
      // El botón de tres puntos vive en el unico div con clase que contiene 'relative shrink-0'
      const card = screen.getByText('Servicio Dominical').closest('div[role="link"]')!;
      const menuContainer = card.querySelector('div.relative.shrink-0')!;
      const menuBtn = within(menuContainer as HTMLElement).getByRole('button');
      fireEvent.click(menuBtn);
      expect(props.onMenuToggle).toHaveBeenCalledWith('ev-1');
    });

    it('con menuOpenId === ev.id muestra opciones Editar/Eliminar que llaman a su callback', () => {
      const props = makeProps({ menuOpenId: 'ev-1' });
      render(<EventCardViews {...props} />);
      fireEvent.click(screen.getByText('Editar'));
      expect(props.onEdit).toHaveBeenCalledWith(expect.objectContaining({ id: 'ev-1' }));
      fireEvent.click(screen.getByText('Eliminar'));
      expect(props.onDelete).toHaveBeenCalledWith('ev-1');
    });

    it('no llama a onMenuToggle al click en Editar/Eliminar (regresión bug menú reabierto)', () => {
      const props = makeProps({ menuOpenId: 'ev-1' });
      render(<EventCardViews {...props} />);
      fireEvent.click(screen.getByText('Editar'));
      fireEvent.click(screen.getByText('Eliminar'));
      expect(props.onMenuToggle).not.toHaveBeenCalled();
    });

    it('badge Cancelado visible cuando status=CANCELLED', () => {
      render(<EventCardViews {...makeProps({ events: [makeEvent({ status: 'CANCELLED', cancellation_reason: 'Lluvia' })] })} />);
      expect(screen.getByText('Cancelado')).toBeInTheDocument();
    });
  });

  describe('list view', () => {
    it('renderiza fila con nombre y badges', () => {
      render(<EventCardViews {...makeProps({ viewType: 'list' })} />);
      expect(screen.getByText('Servicio Dominical')).toBeInTheDocument();
      expect(screen.getByText('Semanal')).toBeInTheDocument();
      expect(screen.getByText('QR')).toBeInTheDocument();
    });

    it('click en nombre dispara onOpenEvent', () => {
      const props = makeProps({ viewType: 'list' });
      render(<EventCardViews {...props} />);
      fireEvent.click(screen.getByText('Servicio Dominical'));
      expect(props.onOpenEvent).toHaveBeenCalledWith('ev-1');
    });
  });

  describe('table view', () => {
    it('renderiza tabla con columnas y datos', () => {
      render(<EventCardViews {...makeProps({ viewType: 'table' })} />);
      const headers = ['Evento', 'Tipo', 'Audiencia', 'Universo', 'Asistencia', 'Fecha visual'];
      headers.forEach((h) => expect(screen.getByText(h)).toBeInTheDocument());
      expect(screen.getByText('Servicio Dominical')).toBeInTheDocument();
      expect(screen.getByText('50%')).toBeInTheDocument();
    });

    it('click en nombre de fila dispara onOpenEvent', () => {
      const props = makeProps({ viewType: 'table' });
      render(<EventCardViews {...props} />);
      fireEvent.click(screen.getByText('Servicio Dominical'));
      expect(props.onOpenEvent).toHaveBeenCalledWith('ev-1');
    });

    it('tabla vacía muestra mensaje', () => {
      render(<EventCardViews {...makeProps({ viewType: 'table', events: [] })} />);
      expect(screen.getByText('No hay eventos registrados')).toBeInTheDocument();
    });
  });
});
