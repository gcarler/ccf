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
  { id: 'email', name: 'Correo', type: 'text', width: 260 },
  { id: 'role', name: 'Rol', type: 'select', width: 150, options: [
    { label: 'Admin', value: 'admin', color: 'blue' },
    { label: 'Editor', value: 'editor', color: 'green' },
    { label: 'Viewer', value: 'viewer', color: 'gray' },
  ]},
  { id: 'department', name: 'Departamento', type: 'text', width: 160 },
  { id: 'active', name: 'Activo', type: 'checkbox', width: 100 },
  { id: 'rating', name: 'Calificación', type: 'rating', width: 130 },
  { id: 'progress', name: 'Progreso', type: 'progress', width: 150 },
  { id: 'joined', name: 'Ingreso', type: 'date', width: 130 },
];

const sampleData = [
  { id: '1', name: 'Juan Pérez', email: 'juan@example.com', role: 'admin', department: 'Tecnología', active: true, rating: 4, progress: 0.75, joined: '2023-01-15' },
  { id: '2', name: 'María González', email: 'maria@example.com', role: 'editor', department: 'Diseño', active: false, rating: 5, progress: 0.3, joined: '2022-11-03' },
  { id: '3', name: 'Carlos López', email: 'carlos@example.com', role: 'editor', department: 'Tecnología', active: true, rating: 3, progress: 0.9, joined: '2021-06-22' },
  { id: '4', name: 'Ana Martínez', email: 'ana@example.com', role: 'viewer', department: 'Marketing', active: true, rating: 4, progress: 0.55, joined: '2024-02-10' },
  { id: '5', name: 'Luis Rodríguez', email: 'luis@example.com', role: 'admin', department: 'Ventas', active: false, rating: 2, progress: 0.1, joined: '2020-09-05' },
  { id: '6', name: 'Sofía Herrera', email: 'sofia@example.com', role: 'editor', department: 'Diseño', active: true, rating: 5, progress: 0.62, joined: '2023-07-18' },
];

const defaultArgs = {
  data: sampleData,
  columns: sampleColumns,
  idAccessor: 'id',
};

export const Default: Story = {
  args: defaultArgs,
};

export const LightMode: Story = {
  parameters: { globals: { theme: 'day' } },
  args: defaultArgs,
};

export const DarkMode: Story = {
  parameters: { globals: { theme: 'night' } },
  args: defaultArgs,
};

export const EmptyState: Story = {
  parameters: { chromatic: { disableSnapshot: true } },
  args: {
    data: [],
    columns: sampleColumns,
    idAccessor: 'id',
    emptyMessage: 'No hay registros para mostrar.',
  },
};

export const ServerSide: Story = {
  parameters: { chromatic: { disableSnapshot: true } },
  args: {
    data: [],
    columns: sampleColumns,
    idAccessor: 'id',
    serverSide: {
      getRows: async ({ offset, limit }) => {
        const all = sampleData.slice(offset, offset + limit);
        return { items: all, total: sampleData.length };
      },
      pageSize: 3,
    },
  },
};

export const Editable: Story = {
  parameters: { chromatic: { disableSnapshot: true } },
  args: {
    data: sampleData,
    columns: sampleColumns,
    idAccessor: 'id',
    onChange: (rowId, columnId, value) => {
      // eslint-disable-next-line no-console
      console.log('onChange', { rowId, columnId, value });
    },
  },
};

export const WithToolbarActions: Story = {
  args: {
    data: sampleData,
    columns: sampleColumns,
    idAccessor: 'id',
    onAddRow: () => ({ id: String(Date.now()), name: 'Nuevo usuario', email: '', role: 'viewer', department: '', active: true, rating: 0, progress: 0, joined: '' }),
    onDeleteRows: (rowIds) => {
      // eslint-disable-next-line no-console
      console.log('onDeleteRows', rowIds);
    },
    actions: [
      {
        label: 'Exportar selección',
        onClick: (selectedRows) => {
          // eslint-disable-next-line no-console
          console.log('Exportar', selectedRows);
        },
      },
    ],
  },
};

export const CompactRows: Story = {
  args: {
    data: sampleData,
    columns: sampleColumns,
    idAccessor: 'id',
    rowHeight: 32,
  },
};

export const ComfortableRows: Story = {
  args: {
    data: sampleData,
    columns: sampleColumns,
    idAccessor: 'id',
    rowHeight: 48,
  },
};
