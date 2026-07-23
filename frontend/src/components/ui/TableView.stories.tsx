import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-quartz.css';
import type { Meta, StoryObj } from '@storybook/react-webpack5';
import TableView, { TableColumn } from './TableView';


const meta: Meta<typeof TableView> = {
  tags: ['autodocs'],
  title: 'UI/TableView',
  component: TableView,
  parameters: {
    layout: 'fullscreen',
  },
};

export default meta;
type Story = StoryObj<typeof TableView>;

const sampleColumns: TableColumn[] = [
  { id: 'name', name: 'Nombre', type: 'text', width: 200 },
  { id: 'email', name: 'Correo', type: 'text', width: 250 },
  { id: 'role', name: 'Rol', type: 'select', width: 150, options: [{ label: 'Admin', value: 'admin' }, { label: 'Editor', value: 'editor' }] },
  { id: 'active', name: 'Activo', type: 'checkbox', width: 100 },
  { id: 'progress', name: 'Progreso', type: 'progress', width: 150 },
];

const sampleData = [
  { id: '1', name: 'Juan Pérez', email: 'juan@example.com', role: 'admin', active: true, progress: 0.75 },
  { id: '2', name: 'María González', email: 'maria@example.com', role: 'editor', active: false, progress: 0.3 },
  { id: '3', name: 'Carlos López', email: 'carlos@example.com', role: 'editor', active: true, progress: 0.9 },
];

export const Default: Story = {
  args: {
    data: sampleData,
    columns: sampleColumns,
    idAccessor: 'id',
  },
};

export const EmptyState: Story = {
  args: {
    data: [],
    columns: sampleColumns,
    idAccessor: 'id',
    emptyMessage: 'No hay registros para mostrar.',
  },
};
