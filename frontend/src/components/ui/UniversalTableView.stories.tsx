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
  tags: string;
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
  { key: 'name', label: 'Nombre', type: 'text', width: '240px' },
  { key: 'status', label: 'Estado', type: 'status', width: '140px' },
  { key: 'priority', label: 'Prioridad', type: 'priority', width: '130px' },
  { key: 'owner', label: 'Responsable', type: 'user', width: '180px' },
  { key: 'due', label: 'Vencimiento', type: 'date', width: '130px' },
  { key: 'progress', label: 'Progreso', type: 'progress', width: '160px' },
  { key: 'tags', label: 'Etiquetas', type: 'text', width: '160px' },
];

// Note: `parameters.chromatic` is only effective once a visual regression tool
// such as Chromatic is installed and wired up. The per-story flags below mark
// non-theme stories as disabled for future automated snapshots.
const sampleData: SampleRow[] = [
  { id: '1', name: 'Diseñar landing', status: 'in_progress', priority: 'high', owner: 'Ana Martínez', due: '2026-07-30', progress: 0.6, tags: 'diseño, web' },
  { id: '2', name: 'Configurar CI/CD', status: 'completed', priority: 'medium', owner: 'Carlos López', due: '2026-07-25', progress: 1, tags: 'devops' },
  { id: '3', name: 'Revisar copy', status: 'pending', priority: 'low', owner: 'María González', due: '2026-08-05', progress: 0, tags: 'contenido' },
  { id: '4', name: 'Migración a TypeScript', status: 'in_progress', priority: 'urgent', owner: 'Luis Rodríguez', due: '2026-07-28', progress: 0.35, tags: 'tech-debt, refactor' },
  { id: '5', name: 'Onboarding usuarios', status: 'review', priority: 'high', owner: 'Sofía Herrera', due: '2026-08-01', progress: 0.8, tags: 'ux' },
  { id: '6', name: 'Auditoría SEO', status: 'blocked', priority: 'medium', owner: 'Ana Martínez', due: '2026-08-10', progress: 0.2, tags: 'marketing' },
  { id: '7', name: 'Optimización de imágenes', status: 'completed', priority: 'low', owner: 'Carlos López', due: '2026-07-20', progress: 1, tags: 'performance' },
  { id: '8', name: 'Tests de regresión', status: 'todo', priority: 'high', owner: 'María González', due: '2026-08-03', progress: 0.1, tags: 'qa' },
];

const defaultArgs = {
  data: sampleData,
  columns: sampleColumns,
};

export const Default: Story = {
  args: {
    ...defaultArgs,
    viewName: 'sample-view',
  },
};

export const LightMode: Story = {
  parameters: { globals: { theme: 'day' } },
  args: {
    ...defaultArgs,
    viewName: 'light-view',
  },
};

export const DarkMode: Story = {
  parameters: { globals: { theme: 'night' } },
  args: {
    ...defaultArgs,
    viewName: 'dark-view',
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

export const Loading: Story = {
  args: {
    data: [],
    columns: sampleColumns,
    viewName: 'loading-view',
    isLoading: true,
  },
};

export const WithRowClick: Story = {
  parameters: { chromatic: { disableSnapshot: true } },
  args: {
    data: sampleData,
    columns: sampleColumns,
    viewName: 'clickable-view',
    onRowClick: () => {},
  },
};

export const GroupedByPriority: Story = {
  args: {
    data: sampleData,
    columns: sampleColumns,
    viewName: 'grouped-priority-view',
    groupBy: 'priority',
  },
};

export const GroupedByStatus: Story = {
  args: {
    data: sampleData,
    columns: sampleColumns,
    viewName: 'grouped-status-view',
    groupBy: 'status',
  },
};

export const Editable: Story = {
  parameters: { chromatic: { disableSnapshot: true } },
  args: {
    data: sampleData,
    columns: sampleColumns,
    viewName: 'editable-view',
    onUpdateItem: async (id, field, value) => {
      // eslint-disable-next-line no-console
      console.log('onUpdateItem', { id, field, value });
      return true;
    },
  },
};

export const WithAddAction: Story = {
  args: {
    data: sampleData,
    columns: sampleColumns,
    viewName: 'add-action-view',
    onAddItem: () => {
      // eslint-disable-next-line no-console
      console.log('onAddItem');
    },
  },
};
