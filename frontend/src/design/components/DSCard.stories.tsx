import type { Meta, StoryObj } from '@storybook/react-webpack5';
import { DSCard } from './DSCard';

const meta: Meta<typeof DSCard> = {
    title: 'Design/Card',
    component: DSCard,
    args: {
        children: (
            <div>
                <h3 className="text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white">Tarjeta premium</h3>
                <p className="text-sm text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] mt-2">Usa este contenedor para métricas, formularios o listas dentro del Workspace.</p>
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
