import type { Meta, StoryObj } from '@storybook/react-webpack5';
import { DSSkeleton } from './DSSkeleton';

const meta: Meta<typeof DSSkeleton> = {
    title: 'Design/Skeleton',
    component: DSSkeleton,
    args: {
        className: 'h-8 w-64',
    },
    parameters: { layout: 'centered' },
};

export default meta;
type Story = StoryObj<typeof DSSkeleton>;

export const Base: Story = {};
export const Rounded: Story = { args: { rounded: 'pill', className: 'h-8 w-72' } };
