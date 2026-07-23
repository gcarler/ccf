import type { Meta, StoryObj } from '@storybook/react-webpack5';
import { DataTable } from './DataTable';

// Sample data for the data table
const sampleData = [
  { id: 1, name: 'Juan Pérez', email: 'juan@example.com', status: 'Activo', age: 34, department: 'Ventas' },
  { id: 2, name: 'María González', email: 'maria@example.com', status: 'Inactivo', age: 28, department: 'Marketing' },
  { id: 3, name: 'Carlos López', email: 'carlos@example.com', status: 'Activo', age: 45, department: 'TI' },
  { id: 4, name: 'Ana Martínez', email: 'ana@example.com', status: 'Pendiente', age: 29, department: 'Recursos Humanos' },
  { id: 5, name: 'Luis Rodriguez', email: 'luis@example.com', status: 'Activo', age: 31, department: 'Finanzas' },
  { id: 6, name: 'Sofia Diaz', email: 'sofia@example.com', status: 'Inactivo', age: 26, department: 'Operaciones' },
];

// Sample columns configuration
const sampleColumns = [
  { 
    header: 'ID', 
    accessorKey: 'id',
    size: 80
  },
  { 
    header: 'Nombre', 
    accessorKey: 'name',
  },
  { 
    header: 'Email', 
    accessorKey: 'email',
  },
  { 
    header: 'Estado', 
    accessorKey: 'status',
  },
  { 
    header: 'Edad', 
    accessorKey: 'age',
    size: 60
  },
  { 
    header: 'Departamento', 
    accessorKey: 'department',
  },
];


const meta: Meta<typeof DataTable> = {
  tags: ['autodocs'],
  title: 'UI/DataTable',
  component: DataTable,
  parameters: {
    layout: 'centered',
  },
};

export default meta;
type Story = StoryObj<typeof DataTable>;

export const Default: Story = {
  args: {
    data: sampleData,
    columns: sampleColumns,
  },
};

export const WithSorting: Story = {
  args: {
    data: sampleData,
    columns: sampleColumns,
  },
  // Note: DataTable handles sorting internally through its state
  // This story demonstrates the initial state
};

export const EmptyState: Story = {
  args: {
    data: [],
    columns: sampleColumns,
  },
};

export const WithColumnSelection: Story = {
  args: {
    data: sampleData,
    columns: [
      { 
        header: 'Nombre completo', 
        accessorKey: 'name',
      },
      { 
        header: 'Correo electrónico', 
        accessorKey: 'email',
      },
    ],
  },
};

export const WithCustomStyling: Story = {
  args: {
    data: sampleData,
    columns: sampleColumns,
  },
  // Note: Styling would be done through CSS classes or modifying the component itself
  // This is just to show the data works
};
