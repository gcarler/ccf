import React from 'react';
import type { Meta, StoryObj } from '@storybook/react-webpack5';
import UniversalTableView, { TableColumn, UniversalTableViewProps } from './UniversalTableView';

interface SampleRow {
  id: string;
  name: string;
  status: string;
  priority: string;
  owner: string;
  due: string;
  progress: number;
}

// Storybook cannot infer the generic T of a component, so we cast it to a
// concrete version typed for SampleRow.
const TypedUniversalTableView = UniversalTableView as React.FC<UniversalTableViewProps<SampleRow>>;


const meta: Meta<typeof TypedUniversalTableView> = {
  tags: ['autodocs'],
  title: 'UI/UniversalTableView',
  component: TypedUniversalTableView,
  parameters: {
    layout: 'fullscreen',
  },
};

export default meta;
type Story = StoryObj<typeof TypedUniversalTableView>;

const sampleColumns: TableColumn<SampleRow>[] = [
  { key: 'name', label: 'Nombre', type: 'text' },
  { key: 'status', label: 'Estado', type: 'status' },
  { key: 'priority', label: 'Prioridad', type: 'priority' },
  { key: 'owner', label: 'Responsable', type: 'user' },
  { key: 'due', label: 'Vencimiento', type: 'date' },
  { key: 'progress', label: 'Progreso', type: 'progress' },
];

const sampleData: SampleRow[] = [
  { id: '1', name: 'Diseñar landing', status: 'in_progress', priority: 'high', owner: 'Ana Martínez', due: '2026-07-30', progress: 0.6 },
  { id: '2', name: 'Configurar CI/CD', status: 'completed', priority: 'medium', owner: 'Carlos López', due: '2026-07-25', progress: 1 },
  { id: '3', name: 'Revisar copy', status: 'pending', priority: 'low', owner: 'María González', due: '2026-08-05', progress: 0 },
];

export const Default: Story = {
  args: {
    data: sampleData,
    columns: sampleColumns,
    viewName: 'sample-view',
  },
};

export const EmptyState: Story = {
  args: {
    data: [],
    columns: sampleColumns,
    viewName: 'empty-view',
    emptyMessage: 'No hay registros para mostrar en esta vista.',
  },
};

export const WithRowClick: Story = {
  args: {
    data: sampleData,
    columns: sampleColumns,
    viewName: 'clickable-view',
    onRowClick: () => {},
  },
};
