import type { Meta, StoryObj } from '@storybook/react-webpack5';
import { DSCommandEntry } from './DSCommandEntry';
import { Home, Search, Settings, User } from 'lucide-react';

const meta: Meta<typeof DSCommandEntry> = {
    title: 'Design/CommandEntry',
    component: DSCommandEntry,
    args: {
        label: 'Command',
    },
    parameters: { layout: 'centered' },
    argTypes: {
        active: { control: 'boolean' },
    },
};

export default meta;
type Story = StoryObj<typeof DSCommandEntry>;

export const Default: Story = {
    args: {
        label: 'Ir a Dashboard',
        shortcut: 'G D',
    },
};

export const Active: Story = {
    args: {
        label: 'CRM Pastoral',
        shortcut: 'G C',
        active: true,
    },
};

export const WithIcon: Story = {
    args: {
        label: 'Ir a Inicio',
        shortcut: 'G H',
        icon: Home,
    },
};

export const WithDescription: Story = {
    args: {
        label: 'Buscar personas',
        shortcut: '/',
        description: 'Busca por nombre, email o teléfono',
        icon: Search,
    },
};

export const ActiveWithIcon: Story = {
    args: {
        label: 'Configuración',
        shortcut: 'G S',
        icon: Settings,
        active: true,
    },
};

export const List: Story = {
    render: () => (
        <div className="w-72 space-y-1">
            <DSCommandEntry label="Ir a Inicio" shortcut="G H" icon={Home} />
            <DSCommandEntry label="Buscar" shortcut="/" icon={Search} />
            <DSCommandEntry label="CRM Pastoral" shortcut="G C" active />
            <DSCommandEntry label="Mi Perfil" shortcut="G P" icon={User} />
            <DSCommandEntry label="Configuración" shortcut="G S" icon={Settings} />
        </div>
    ),
};
