import type { Meta, StoryObj } from '@storybook/react-webpack5';
import { DSMetric } from './DSMetric';

const meta: Meta<typeof DSMetric> = {
    title: 'Design/Metric',
    component: DSMetric,
    args: {
        label: 'Participantes activos',
        value: '1,248',
        trend: '+12% vs semana pasada',
    },
    parameters: { layout: 'centered' },
};

export default meta;
type Story = StoryObj<typeof DSMetric>;

export const Sky: Story = { args: { tone: 'blue' } };
export const Emerald: Story = { args: { tone: 'emerald' } };
export const Amber: Story = { args: { tone: 'amber' } };
