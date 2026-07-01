import type { Meta, StoryObj } from '@storybook/react-webpack5';
import { DSButton } from './DSButton';

const meta: Meta<typeof DSButton> = {
    title: 'Design/Button',
    component: DSButton,
    args: {
        children: 'Button',
    },
    parameters: { layout: 'centered' },
    argTypes: {
        variant: {
            control: 'select',
            options: ['primary', 'secondary', 'ghost'],
        },
        loading: { control: 'boolean' },
        disabled: { control: 'boolean' },
    },
};

export default meta;
type Story = StoryObj<typeof DSButton>;

export const Primary: Story = { args: { variant: 'primary' } };
export const Secondary: Story = { args: { variant: 'secondary' } };
export const Ghost: Story = { args: { variant: 'ghost' } };
export const Loading: Story = { args: { loading: true } };
export const Disabled: Story = { args: { disabled: true } };
