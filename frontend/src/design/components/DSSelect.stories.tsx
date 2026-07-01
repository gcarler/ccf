import React from 'react';
import type { Meta, StoryObj } from '@storybook/react-webpack5';
import { DSSelect } from './DSSelect';

const meta: Meta<typeof DSSelect> = {
    title: 'Design/Select',
    component: DSSelect,
    parameters: { layout: 'centered' },
    argTypes: {
        disabled: { control: 'boolean' },
    },
};

export default meta;
type Story = StoryObj<typeof DSSelect>;

const sampleOptions = [
    { value: '', label: 'Seleccionar...' },
    { value: 'option1', label: 'Opción 1' },
    { value: 'option2', label: 'Opción 2' },
    { value: 'option3', label: 'Opción 3' },
];

export const Default: Story = {
    args: {
        options: sampleOptions,
    },
};

export const WithLabel: Story = {
    args: {
        label: 'País',
        options: sampleOptions,
    },
};

export const WithPlaceholder: Story = {
    args: {
        label: 'País',
        placeholder: 'Selecciona un país',
        options: sampleOptions,
    },
};

export const WithError: Story = {
    args: {
        label: 'País',
        options: sampleOptions,
        error: 'Campo requerido',
    },
};

export const WithHelperText: Story = {
    args: {
        label: 'Rol',
        options: sampleOptions,
        helperText: 'Selecciona el rol del usuario',
    },
};

export const Disabled: Story = {
    args: {
        label: 'País',
        options: sampleOptions,
        disabled: true,
    },
};

export const FormExample: Story = {
    render: () => (
        <div className="w-64 space-y-4">
            <DSSelect 
                label="País" 
                placeholder="Selecciona un país"
                options={[
                    { value: 'mx', label: 'México' },
                    { value: 'co', label: 'Colombia' },
                    { value: 'ar', label: 'Argentina' },
                    { value: 'cl', label: 'Chile' },
                ]}
            />
            <DSSelect 
                label="Rol" 
                options={[
                    { value: 'admin', label: 'Administrador' },
                    { value: 'user', label: 'Usuario' },
                    { value: 'viewer', label: 'Visor' },
                ]}
            />
            <DSSelect 
                label="Estado" 
                error="Selecciona un estado"
                options={sampleOptions}
            />
        </div>
    ),
};
