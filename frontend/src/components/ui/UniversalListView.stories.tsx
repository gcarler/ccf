import type { Meta, StoryObj } from '@storybook/react-webpack5';
import UniversalListView from './UniversalListView';
import type { ListItem } from './UniversalListView';

const sampleItems: ListItem[] = [
  { id: 1, title: 'Preparar informe mensual', description: 'Recopilar datos de asistencia y ofrendas del mes', status: 'in_progress', priority: 'high', assignee: 'Juan Pérez', date: '2026-07-25', tags: ['finanzas'] },
  { id: 2, title: 'Organizar reunión de líderes', description: 'Coordinar agenda y logística para la reunión trimestral', status: 'todo', priority: 'medium', assignee: 'María González', date: '2026-08-01', tags: ['liderazgo'] },
  { id: 3, title: 'Actualizar directorio', description: 'Revisar y actualizar información de contacto de miembros', status: 'completed', priority: 'low', assignee: 'Carlos López', date: '2026-07-20', tags: ['administración'] },
  { id: 4, title: 'Planificar campamento juvenil', description: 'Buscar lugar, presupuesto y agenda para el retiro de jóvenes', status: 'in_progress', priority: 'urgent', assignee: 'Ana Martínez', date: '2026-08-15', tags: ['jóvenes'] },
];

const meta: Meta<typeof UniversalListView> = {
  title: 'UI/UniversalListView',
  component: UniversalListView,
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof UniversalListView>;

export const Default: Story = {
  args: {
    items: sampleItems,
    onItemClick: (item) => console.log('Item clicked:', item),
    title: 'Lista de tareas',
  },
};

export const EmptyState: Story = {
  args: {
    items: [],
    title: 'Sin tareas',
    emptyMessage: 'No hay tareas pendientes para mostrar.',
    onItemClick: (item) => console.log('Item clicked:', item),
  },
};

export const Searchable: Story = {
  args: {
    items: sampleItems,
    searchable: true,
    title: 'Tareas (búsqueda habilitada)',
    onItemClick: (item) => console.log('Item clicked:', item),
  },
};

export const WithCreation: Story = {
  args: {
    items: sampleItems,
    title: 'Tareas del proyecto',
    onCreate: () => console.log('Create new item'),
    onItemClick: (item) => console.log('Item clicked:', item),
  },
};

export const SingleItem: Story = {
  args: {
    items: [sampleItems[0]],
    title: 'Tarea única',
    onItemClick: (item) => console.log('Item clicked:', item),
  },
};