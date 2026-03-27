import type { Meta, StoryObj } from '@storybook/react-webpack5';
import { DSSectionHeader } from './DSSectionHeader';
import { DSToolbarChip } from './DSToolbarChip';

const meta: Meta<typeof DSSectionHeader> = {
    title: 'Design/SectionHeader',
    component: DSSectionHeader,
    args: {
        eyebrow: 'Academia',
        title: 'Plan de estudio sugerido',
        description: 'Selecciona la ruta que optimus brain preparó para ti esta semana.',
    },
    parameters: { layout: 'centered' },
};

export default meta;
type Story = StoryObj<typeof DSSectionHeader>;

export const Default: Story = {};
export const WithActions: Story = {
    args: {
        actions: (
            <div className="flex gap-2">
                <DSToolbarChip label="Semana" active />
                <DSToolbarChip label="Mes" />
            </div>
        ),
    },
};
