import type { Meta, StoryObj } from '@storybook/react-webpack5';
import { DSButton } from './DSButton';

const meta: Meta<typeof DSButton> = {
    title: 'Design/DSButton',
    component: DSButton,
    args: {
        children: 'Command',
    },
    parameters: {
        layout: 'centered',
    },
};

export default meta;
type Story = StoryObj<typeof DSButton>;

export const Primary: Story = {
    args: {
        variant: 'primary',
    },
};

export const Secondary: Story = {
    args: {
        variant: 'secondary',
    },
};

export const Ghost: Story = {
    args: {
        variant: 'ghost',
    },
};
