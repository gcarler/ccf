import type { Meta, StoryObj } from '@storybook/react-webpack5';
import { DSBadge } from './DSBadge';

const meta: Meta<typeof DSBadge> = {
    title: 'Design/Badge',
    component: DSBadge,
    args: {
        label: 'Academia',
    },
    parameters: {
        layout: 'centered',
    },
};

export default meta;
type Story = StoryObj<typeof DSBadge>;

export const Slate: Story = { args: { tone: 'slate' } };
export const Blue: Story = { args: { tone: 'blue' } };
export const Emerald: Story = { args: { tone: 'emerald' } };
