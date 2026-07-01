import React from 'react';
import type { Meta, StoryObj } from '@storybook/react-webpack5';
import { DSInput } from './DSInput';
import { Search, Mail, Lock } from 'lucide-react';

const meta: Meta<typeof DSInput> = {
    title: 'Design/Input',
    component: DSInput,
    parameters: { layout: 'centered' },
    argTypes: {
        disabled: { control: 'boolean' },
        loading: { control: 'boolean' },
    },
};

export default meta;
type Story = StoryObj<typeof DSInput>;

export const Default: Story = {
    args: {
        placeholder: 'Enter text...',
    },
};

export const WithLabel: Story = {
    args: {
        label: 'Email',
        placeholder: 'correo@ejemplo.com',
    },
};

export const WithError: Story = {
    args: {
        label: 'Email',
        value: 'invalid-email',
        error: 'Email inválido',
    },
};

export const WithHelperText: Story = {
    args: {
        label: 'Password',
        type: 'password',
        helperText: 'Mínimo 8 caracteres',
    },
};

export const WithIcon: Story = {
    args: {
        label: 'Search',
        placeholder: 'Buscar...',
        icon: Search,
    },
};

export const Disabled: Story = {
    args: {
        label: 'Email',
        value: 'disabled@email.com',
        disabled: true,
    },
};

export const Loading: Story = {
    args: {
        label: 'Email',
        value: 'loading...',
        loading: true,
    },
};

export const FormExample: Story = {
    render: () => (
        <div className="w-64 space-y-4">
            <DSInput label="Nombre" placeholder="Tu nombre" />
            <DSInput label="Email" placeholder="correo@ejemplo.com" icon={Mail} />
            <DSInput label="Contraseña" type="password" placeholder="••••••••" icon={Lock} />
            <DSInput 
                label="Buscar" 
                placeholder="Buscar personas..." 
                icon={Search}
                helperText="Presiona Enter para buscar"
            />
        </div>
    ),
};

export const ErrorStates: Story = {
    render: () => (
        <div className="w-64 space-y-4">
            <DSInput label="Email" error="Email requerido" />
            <DSInput label="Password" error="Mínimo 8 caracteres" />
            <DSInput label="Phone" error="Formato inválido" />
        </div>
    ),
};
