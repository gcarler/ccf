import type { Meta, StoryObj } from '@storybook/react-webpack5';
import StatusPicker from './StatusPicker';


const meta: Meta<typeof StatusPicker> = {
  tags: ['autodocs'],
  title: 'UI/StatusPicker',
  component: StatusPicker,
  parameters: {
    layout: 'centered',
  },
};

export default meta;
type Story = StoryObj<typeof StatusPicker>;

const statusOptions = [
  {
    label: 'Pendiente',
    value: 'pending',
    color: 'bg-[hsl(var(--text-secondary))]/20',
    text: 'text-[hsl(var(--text-secondary))]',
    bg: 'bg-[hsl(var(--surface-2))]',
  },
  {
    label: 'En Progreso',
    value: 'in_progress',
    color: 'bg-[hsl(var(--primary))]/20',
    text: 'text-[hsl(var(--primary))]',
    bg: 'bg-info-soft',
  },
  {
    label: 'En Revisión',
    value: 'review',
    color: 'bg-[hsl(var(--warning)/0.2)]',
    text: 'text-warning-text',
    bg: 'bg-warning-soft',
  },
  {
    label: 'Completado',
    value: 'completed',
    color: 'bg-[hsl(var(--success)/0.2)]',
    text: 'text-success-text',
    bg: 'bg-success-soft',
  },
];

export const Default: Story = {
  args: {
    currentValue: 'in_progress',
    options: statusOptions,
    onSelect: (value) => {
      console.log('Selected status:', value);
    },
  },
};

export const WithCustomColors: Story = {
  args: {
    currentValue: 'review',
    options: [
      {
        label: 'Bajo',
        value: 'low',
        color: 'bg-[hsl(var(--text-secondary))]/20',
        text: 'text-[hsl(var(--text-secondary))]',
        bg: 'bg-[hsl(var(--surface-2))]',
      },
      {
        label: 'Medio',
        value: 'medium',        color: 'bg-[hsl(var(--warning)/0.2)]',
    text: 'text-warning-text',
    bg: 'bg-warning-soft',
      },
      {
        label: 'Alto',
        value: 'high',
        color: 'bg-[hsl(var(--danger))]/20',
        text: 'text-[hsl(var(--danger))]',
        bg: 'bg-[hsl(var(--danger))]/10',
      },
    ],
    onSelect: (value) => {
      console.log('Selected priority:', value);
    },
  },
};

export const Disabled: Story = {
  args: {
    currentValue: 'completed',
    options: statusOptions,
    onSelect: (value) => {
      console.log('Selected status:', value);
    },
    className: 'opacity-50 pointer-events-none',
  },
};

export const SingleOption: Story = {
  args: {
    currentValue: 'pending',
    options: [
      {
        label: 'Solo Opción',
        value: 'only',        color: 'bg-[hsl(var(--primary))]/20',
    text: 'text-[hsl(var(--primary))]',
    bg: 'bg-info-soft',
      },
    ],
    onSelect: (value) => {
      console.log('Selected:', value);
    },
  },
};

export const WithLabel: Story = {
  args: {
    currentValue: 'in_progress',
    options: statusOptions,
    onSelect: (value) => {
      console.log('Selected status:', value);
    },
  },
  render: (args) => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
      <div className="text-[hsl(var(--text-secondary))] font-medium">
        Estado actual:
      </div>
      <StatusPicker {...args} />
    </div>
  ),
};