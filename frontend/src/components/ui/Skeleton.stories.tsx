import type { Meta, StoryObj } from '@storybook/react-webpack5';
import Skeleton from './Skeleton';

const meta: Meta<typeof Skeleton> = {
  title: 'UI/Skeleton',
  component: Skeleton,
};

export default meta;
type Story = StoryObj<typeof Skeleton>;

export const Default: Story = {
  args: {},
};

export const DifferentSizes: Story = {
  args: {},
  render: (args) => (
    <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
      <Skeleton {...args} className="w-16 h-4" />
      <Skeleton {...args} className="w-24 h-6" />
      <Skeleton {...args} className="w-32 h-8" />
      <Skeleton {...args} className="w-40 h-10" />
      <Skeleton {...args} className="w-48 h-12" />
    </div>
  ),
};

export const InCard: Story = {
  args: {},
  render: () => (
    <div className="p-4 bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] rounded-lg shadow-md w-64">
      <div className="space-y-4">
        <div className="flex items-center space-x-3">
          <Skeleton className="w-10 h-10 rounded-full" />
          <div className="space-y-2">
            <Skeleton className="w-32 h-4" />
            <Skeleton className="w-48 h-4" />
          </div>
        </div>
        <Skeleton className="w-full h-6 mt-2" />
        <Skeleton className="w-full h-4 mt-2" />
        <div className="mt-4 space-y-2">
          <Skeleton className="w-16 h-2" />
          <Skeleton className="w-24 h-2" />
          <Skeleton className="w-32 h-2" />
        </div>
      </div>
    </div>
  ),
};

export const Circle: Story = {
  args: {},
  render: () => (
    <div className="flex items-center space-x-4">
      <Skeleton className="w-8 h-8 rounded-full" />
      <Skeleton className="w-10 h-10 rounded-full" />
      <Skeleton className="w-12 h-12 rounded-full" />
      <Skeleton className="w-16 h-16 rounded-full" />
      <Skeleton className="w-20 h-20 rounded-full" />
    </div>
  ),
};