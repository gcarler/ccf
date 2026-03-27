import type { Meta, StoryObj } from '@storybook/react-webpack5';
import { DSCard } from './DSCard';

const meta: Meta<typeof DSCard> = {
    title: 'Design/Card',
    component: DSCard,
    args: {
        children: (
            <div>
                <h3 className="text-xl font-bold text-slate-900 dark:text-white">Tarjeta premium</h3>
                <p className="text-sm text-slate-500 dark:text-slate-300 mt-2">Usa este contenedor para métricas, formularios o listas dentro del Workspace.</p>
            </div>
        ),
    },
    parameters: { layout: 'centered' },
};

export default meta;
type Story = StoryObj<typeof DSCard>;

export const Glass: Story = {};
export const Dark: Story = { args: { tone: 'dark' } };
export const Light: Story = { args: { tone: 'light' } };
