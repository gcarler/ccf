import type { Meta, StoryObj } from '@storybook/react-webpack5';
import UniversalListView, { ListItem } from './UniversalListView';


const meta: Meta<typeof UniversalListView> = {
  tags: ['autodocs'],
  title: 'UI/UniversalListView',
  component: UniversalListView,
  parameters: {
    layout: 'centered',
  },
};

export default meta;
type Story = StoryObj<typeof UniversalListView>;

const sampleItems: ListItem[] = [
  {
    id: '1',
    title: 'Revisar propuesta de proyecto',
    description: 'Analizar alcance, costos y cronograma entregados por el cliente.',
    status: 'in_progress',
    priority: 'high',
    assignee: 'María González',
    date: '2026-07-25',
    tags: ['ventas', 'urgente'],
  },
  {
    id: '2',
    title: 'Actualizar documentación técnica',
    description: 'Incluir los nuevos endpoints del módulo de donaciones.',
    status: 'pending',
    priority: 'medium',
    assignee: 'Carlos López',
    date: '2026-07-28',
    tags: ['docs'],
  },
  {
    id: '3',
    title: 'Desplegar hotfix de seguridad',
    description: 'Aplicar parche de dependencias y validar en staging.',
    status: 'completed',
    priority: 'urgent',
    assignee: 'Ana Martínez',
    date: '2026-07-23',
    tags: ['devops', 'seguridad'],
  },
  {
    id: '4',
    title: 'Diseñar landing de evento',
    description: 'Crear mockups responsivos para la jornada de oración.',
    status: 'open',
    priority: 'low',
    assignee: 'Luis Rodríguez',
    date: '2026-08-01',
  },
];

export const Default: Story = {
  args: {
    items: sampleItems,
    title: 'Tareas pendientes',
  },
};

export const WithSearch: Story = {
  args: {
    items: sampleItems,
    title: 'Tareas con búsqueda',
    searchable: true,
  },
};

export const WithActions: Story = {
  args: {
    items: sampleItems,
    title: 'Tareas con acciones',
    searchable: true,
    onCreate: () => {},
    onDelete: () => {},
    onItemClick: () => {},
  },
};

export const EmptyState: Story = {
  args: {
    items: [],
    title: 'Sin elementos',
    emptyMessage: 'No hay tareas para mostrar en esta vista.',
  },
};

export const CustomColumns: Story = {
  args: {
    items: sampleItems,
    title: 'Vista de seguimiento',
    columns: [
      { key: 'title', label: 'Actividad' },
      { key: 'assignee', label: 'Responsable' },
      { key: 'date', label: 'Fecha límite' },
    ],
  },
};
