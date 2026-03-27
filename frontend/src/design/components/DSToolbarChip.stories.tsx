import type { Meta, StoryObj } from '@storybook/react-webpack5';
import { DSToolbarChip } from './DSToolbarChip';

const meta: Meta<typeof DSToolbarChip> = {
    title: 'Design/ToolbarChip',
    component: DSToolbarChip,
    args: {
        label: 'Todos',
    },
    parameters: { layout: 'centered' },
};

export default meta;
type Story = StoryObj<typeof DSToolbarChip>;

export const Soft: Story = { args: { variant: 'soft' } };
export const Solid: Story = { args: { active: true } };
export const Outline: Story = { args: { variant: 'outline' } };
