import type { Meta, StoryObj } from '@storybook/react-webpack5';
import UniversalGanttView from './UniversalGanttView';
import type { GanttItem } from './UniversalGanttView';

const today = new Date().toISOString().split('T')[0];
const tomorrow = new Date(Date.now() + 86400000).toISOString().split('T')[0];
const day3 = new Date(Date.now() + 3 * 86400000).toISOString().split('T')[0];
const day5 = new Date(Date.now() + 5 * 86400000).toISOString().split('T')[0];
const day7 = new Date(Date.now() + 7 * 86400000).toISOString().split('T')[0];
const day14 = new Date(Date.now() + 14 * 86400000).toISOString().split('T')[0];
const day30 = new Date(Date.now() + 30 * 86400000).toISOString().split('T')[0];
const day_minus7 = new Date(Date.now() - 7 * 86400000).toISOString().split('T')[0];

const sampleItems: GanttItem[] = [
  { id: 1, title: 'Preparar informe mensual', subtitle: 'Finanzas', start_date: day_minus7, end_date: day3, color: 'blue', progress: 60 },
  { id: 2, title: 'Organizar retiro juvenil', subtitle: 'Jóvenes', start_date: day3, end_date: day14, color: 'emerald', progress: 30 },
  { id: 3, title: 'Campaña de evangelismo', subtitle: 'Evangelismo', start_date: day5, end_date: day30, color: 'amber', progress: 15 },
  { id: 4, title: 'Revisión de miembros', subtitle: 'CRM', start_date: today, end_date: day7, color: 'sky', progress: 80 },
  { id: 5, title: 'Evento de recaudación', subtitle: 'Finanzas', start_date: tomorrow, end_date: day5, color: 'rose', progress: 0 },
];


const meta: Meta<typeof UniversalGanttView> = {
  tags: ['autodocs'],
  title: 'UI/UniversalGanttView',
  component: UniversalGanttView,
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof UniversalGanttView>;

export const Default: Story = {
  args: {
    items: sampleItems,
    moduleName: 'Proyectos',
    onItemClick: (item) => console.log('Item clicked:', item),
  },
};

export const EmptyState: Story = {
  args: {
    items: [],
    moduleName: 'Sin proyectos',
    onItemClick: (item) => console.log('Item clicked:', item),
  },
};

export const SingleItem: Story = {
  args: {
    items: [sampleItems[0]],
    moduleName: 'Tarea única',
    onItemClick: (item) => console.log('Item clicked:', item),
  },
};

export const WithOptimization: Story = {
  args: {
    items: sampleItems,
    moduleName: 'Proyectos',
    onItemClick: (item) => console.log('Item clicked:', item),
    onOptimize: () => console.log('Optimize clicked'),
  },
};