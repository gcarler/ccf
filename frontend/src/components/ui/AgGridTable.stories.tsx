import React from 'react';
import type { Meta, StoryObj } from '@storybook/react-webpack5';
import AgGridTable, { ColDef, type AgGridTableProps } from './AgGridTable';

interface SampleRow {
  id: string;
  name: string;
  role: string;
  active: boolean;
  progress: number;
}

// Storybook cannot infer the generic T of a component, so we cast it to a
// concrete version typed for SampleRow.
const TypedAgGridTable = AgGridTable as React.FC<AgGridTableProps<SampleRow>>;

const meta: Meta<typeof TypedAgGridTable> = {
  tags: ['autodocs'],
  title: 'UI/AgGridTable',
  component: TypedAgGridTable,
  parameters: {
    layout: 'fullscreen',
  },
};

export default meta;
type Story = StoryObj<typeof TypedAgGridTable>;

const columns: ColDef<SampleRow>[] = [
  { field: 'name', headerName: 'Nombre', sortable: true, filter: true, flex: 1 },
  { field: 'role', headerName: 'Rol', sortable: true, filter: true, flex: 1 },
  { field: 'active', headerName: 'Activo', cellDataType: 'boolean', width: 100 },
  { field: 'progress', headerName: 'Progreso', cellDataType: 'number', width: 120 },
];

const sampleData: SampleRow[] = [
  { id: '1', name: 'Juan Pérez', role: 'Admin', active: true, progress: 75 },
  { id: '2', name: 'María González', role: 'Editor', active: false, progress: 30 },
  { id: '3', name: 'Carlos López', role: 'Viewer', active: true, progress: 90 },
  { id: '4', name: 'Ana Martínez', role: 'Editor', active: true, progress: 55 },
  { id: '5', name: 'Luis Rodríguez', role: 'Admin', active: false, progress: 10 },
];

export const Default: Story = {
  args: {
    rowData: sampleData,
    columnDefs: columns,
    density: 'default',
  },
};

export const Compact: Story = {
  args: {
    ...Default.args,
    density: 'compact',
  },
};

export const Comfortable: Story = {
  args: {
    ...Default.args,
    density: 'comfortable',
  },
};

export const EmptyState: Story = {
  args: {
    rowData: [],
    columnDefs: columns,
    density: 'default',
  },
};

export const ManyRows: Story = {
  args: {
    rowData: Array.from({ length: 50 }, (_, i) => ({
      id: String(i + 1),
      name: `Usuario ${i + 1}`,
      role: i % 3 === 0 ? 'Admin' : i % 3 === 1 ? 'Editor' : 'Viewer',
      active: i % 2 === 0,
      progress: Math.round((i / 50) * 100),
    })),
    columnDefs: columns,
    density: 'compact',
  },
};
