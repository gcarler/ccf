import type { Meta, StoryObj } from '@storybook/react-webpack5';
import SplitDropdownButton from './SplitDropdownButton';
import { Plus, FileText, Bell, LayoutDashboard, Layout, List } from 'lucide-react';

const meta: Meta<typeof SplitDropdownButton> = {
  title: 'UI/SplitDropdownButton',
  component: SplitDropdownButton,
  parameters: {
    layout: 'centered',
  },
};

export default meta;
type Story = StoryObj<typeof SplitDropdownButton>;

const defaultOptions = [
  { id: 'task', label: 'Tarea', icon: Plus },
  { id: 'document', label: 'Documento', icon: FileText },
  { id: 'reminder', label: 'Recordatorio', icon: Bell },
  { id: 'whiteboard', label: 'Pizarra', icon: LayoutDashboard },
  { id: 'panel', label: 'Panel', icon: Layout },
];

export const Default: Story = {
  args: {
    onMainClick: () => {
      alert('Main button clicked');
    },
    onOptionClick: (id) => {
      alert(`Option clicked: ${id}`);
    },
    mainLabel: 'Nuevo',
    options: defaultOptions,
  },
};

export const WithCustomLabel: Story = {
  args: {
    onMainClick: () => {
      alert('Create project clicked');
    },
    onOptionClick: (id) => {
      alert(`Option selected: ${id}`);
    },
    mainLabel: 'Crear Proyecto',
    options: [
      { id: 'project', label: 'Proyecto', icon: Layout },
      { id: 'template', label: 'Desde plantilla', icon: Layout },
      { id: 'import', label: 'Importar', icon: LayoutDashboard },
    ],
  },
};

export const WithCustomIcon: Story = {
  args: {
    onMainClick: () => {
      alert('Quick add clicked');
    },
    onOptionClick: (id) => {
      alert(`Quick item: ${id}`);
    },
    mainLabel: 'Agregar',
    icon: Plus,
    options: [
      { id: 'note', label: 'Nota', icon: Layout },
      { id: 'checklist', label: 'Lista de verificación', icon: List },
      { id: 'reminder', label: 'Recordatorio', icon: Bell },
    ],
  },
};

export const Disabled: Story = {
  args: {
    onMainClick: () => {
      // Disabled - no action
    },
    onOptionClick: (id) => {
      // Disabled - no action
    },
    mainLabel: 'Acción',
    options: defaultOptions,
  },
  // We'll simulate disabled by wrapping in a div with pointer-events-none
  render: (args) => (
    <div className="pointer-events-none opacity-50">
      <SplitDropdownButton {...args} />
    </div>
  ),
};

export const Minimal: Story = {
  args: {
    onMainClick: () => {
      alert('Main action');
    },
    mainLabel: 'Ejecutar',
    options: [
      { id: 'run', label: 'Ejecutar', icon: Layout },
      { id: 'debug', label: 'Depurar', icon: Layout },
    ],
  },
};