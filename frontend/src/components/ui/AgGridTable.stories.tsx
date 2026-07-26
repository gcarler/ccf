import React from 'react';
import type { Meta, StoryObj } from '@storybook/react-webpack5';
import AgGridTable, { ColDef, type AgGridTableProps, type GridReadyEvent } from './AgGridTable';

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
  decorators: [
    // Give the grid a stable, constrained height so visual snapshots are
    // deterministic across browsers and runs.
    (Story) => (
      <div style={{ height: 420, width: '100%' }}>
        <Story />
      </div>
    ),
  ],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof TypedAgGridTable>;

// Shared args for light/dark regression snapshots.
// Note: for automated visual regression in CI, wire these stories to a
// snapshot tool such as Chromatic (currently not installed in this project).

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

const regressionArgs = {
  rowData: sampleData,
  columnDefs: columns,
  density: 'default' as const,
};

export const Default: Story = {
  args: regressionArgs,
};

function SelectedRowStory() {
  const onGridReady = React.useCallback((event: GridReadyEvent<SampleRow>) => {
    // Select the first row once the grid API is available.
    event.api?.getRowNode?.(sampleData[0]?.id ?? '1')?.setSelected(true);
  }, []);

  return <TypedAgGridTable {...regressionArgs} onGridReady={onGridReady} />;
}

/**
 * Snapshot story with the first row pre-selected.
 * Useful to catch regressions in selection highlight styles.
 */
export const SelectedRow: Story = {
  render: () => <SelectedRowStory />,
};

// The stories below are useful for manual exploration but excluded from
// automated visual regression snapshots because they are variations of the same
// component state. `parameters.chromatic` is only effective once a visual
// regression tool (e.g. Chromatic) is installed and wired up.
export const Compact: Story = {
  parameters: { chromatic: { disableSnapshot: true } },
  args: {
    ...regressionArgs,
    density: 'compact',
  },
};

export const Comfortable: Story = {
  parameters: { chromatic: { disableSnapshot: true } },
  args: {
    ...regressionArgs,
    density: 'comfortable',
  },
};

export const EmptyState: Story = {
  parameters: { chromatic: { disableSnapshot: true } },
  args: {
    ...regressionArgs,
    rowData: [],
  },
};

export const ManyRows: Story = {
  parameters: { chromatic: { disableSnapshot: true } },
  args: {
    ...regressionArgs,
    rowData: Array.from({ length: 50 }, (_, i) => ({
      id: String(i + 1),
      name: `Usuario ${i + 1}`,
      role: i % 3 === 0 ? 'Admin' : i % 3 === 1 ? 'Editor' : 'Viewer',
      active: i % 2 === 0,
      progress: Math.round((i / 50) * 100),
    })),
    density: 'compact',
  },
};

/**
 * Snapshot story that pins the global Storybook theme to "day".
 * Use this story for visual regression in light mode.
 */
export const LightMode: Story = {
  parameters: {
    globals: {
      theme: 'day',
    },
  },
  args: regressionArgs,
};

/**
 * Snapshot story that pins the global Storybook theme to "night".
 * Use this story for visual regression in dark mode.
 */
export const DarkMode: Story = {
  parameters: {
    globals: {
      theme: 'night',
    },
  },
  args: regressionArgs,
};
