import type { Meta, StoryObj } from '@storybook/react-webpack5';
import { DSChart } from './DSChart';

const sampleData = [
    { label: 'Ene', value: 40 },
    { label: 'Feb', value: 65 },
    { label: 'Mar', value: 45 },
    { label: 'Abr', value: 80 },
    { label: 'May', value: 55 },
    { label: 'Jun', value: 90 },
];

const meta: Meta<typeof DSChart> = {
    title: 'Design/Chart',
    component: DSChart,
    args: {
        data: sampleData,
        height: 250,
        color: 'hsl(var(--primary))',
    },
    parameters: { layout: 'centered' },
    argTypes: {
        type: {
            control: 'select',
            options: ['line', 'area', 'bar'],
        },
        height: { control: 'number' },
        color: { control: 'color' },
    },
};

export default meta;
type Story = StoryObj<typeof DSChart>;

export const Line: Story = { args: { type: 'line' } };
export const Area: Story = { args: { type: 'area' } };
export const Bar: Story = { args: { type: 'bar' } };
export const Emerald: Story = { args: { type: 'line', color: 'hsl(var(--success))' } };
export const Compact: Story = { args: { type: 'bar', height: 150, color: 'hsl(var(--warning))' } };
