import type { Meta, StoryObj } from '@storybook/react-webpack5';
import UniversalCalendarView from './UniversalCalendarView';
import type { CalendarEvent } from './UniversalCalendarView';

const sampleEvents: CalendarEvent[] = [
  { id: 1, title: 'Reunión de líderes', date: new Date().toISOString().split('T')[0], time: '10:00', color: 'blue', type: 'once', location: 'Sala principal' },
  { id: 2, title: 'Culto de jóvenes', date: new Date(Date.now() + 86400000 * 3).toISOString().split('T')[0], time: '19:00', color: 'emerald', type: 'annual', location: 'Auditorio' },
  { id: 3, title: 'Cumpleaños Pastor', date: new Date(Date.now() + 86400000 * 5).toISOString().split('T')[0], color: 'amber', type: 'annual' },
  { id: 4, title: 'Reunión de células', date: new Date(Date.now() + 86400000 * 7).toISOString().split('T')[0], time: '18:30', color: 'sky', type: 'permanent' },
  { id: 5, title: 'Evento especial', date: new Date(Date.now() - 86400000 * 2).toISOString().split('T')[0], time: '15:00', color: 'rose', type: 'once' },
];


const meta: Meta<typeof UniversalCalendarView> = {
  tags: ['autodocs'],
  title: 'UI/UniversalCalendarView',
  component: UniversalCalendarView,
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof UniversalCalendarView>;

export const Default: Story = {
  args: {
    events: sampleEvents,
    title: 'Calendario de eventos',
    onDateClick: (date) => console.log('Date clicked:', date),
    onEventClick: (event) => console.log('Event clicked:', event),
  },
};

export const EmptyState: Story = {
  args: {
    events: [],
    title: 'Sin eventos',
    onDateClick: (date) => console.log('Date clicked:', date),
  },
};

export const WithCreation: Story = {
  args: {
    events: sampleEvents,
    title: 'Calendario de actividades',
    onCreate: () => console.log('Create event'),
    onEventClick: (event) => console.log('Event clicked:', event),
  },
};

export const SingleEvent: Story = {
  args: {
    events: [sampleEvents[0]],
    title: 'Próximo evento',
    onDateClick: (date) => console.log('Date clicked:', date),
  },
};

export const AllDayEvent: Story = {
  args: {
    events: sampleEvents.map(e => ({ ...e, time: undefined })),
    title: 'Eventos de todo el día',
    onEventClick: (event) => console.log('Event clicked:', event),
  },
};