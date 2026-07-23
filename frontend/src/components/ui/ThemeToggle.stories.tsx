import type { Meta, StoryObj } from '@storybook/react-webpack5';
import ThemeToggle from './ThemeToggle';

const meta: Meta<typeof ThemeToggle> = {
  title: 'UI/ThemeToggle',
  component: ThemeToggle,
  parameters: {
    layout: 'centered',
  },
  decorators: [
    (Story) => {
      if (typeof window !== 'undefined') {
        (window as any).__STORYBOOK__ = true;
      }
      return (
        <div className="p-8 bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] rounded-lg flex items-center justify-center">
          <Story />
        </div>
      );
    },
  ],
};

export default meta;
type Story = StoryObj<typeof ThemeToggle>;

export const IconVariant: Story = {
  args: {
    variant: 'icon',
  },
};

export const PillVariant: Story = {
  args: {
    variant: 'pill',
  },
};

export const RowVariant: Story = {
  args: {
    variant: 'row',
  },
};

export const WithCustomClass: Story = {
  args: {
    variant: 'pill',
    className: 'shadow-md',
  },
};

export const AllVariants: Story = {
  args: {
    variant: 'icon',
  },
  render: () => (
    <div className="flex flex-col gap-6" style={{ width: '300px' }}>
      <div>
        <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-2">Icono</p>
        <ThemeToggle variant="icon" />
      </div>
      <div>
        <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-2">Pill</p>
        <ThemeToggle variant="pill" />
      </div>
      <div>
        <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-2">Fila</p>
        <ThemeToggle variant="row" />
      </div>
    </div>
  ),
};