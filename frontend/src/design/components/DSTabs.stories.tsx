import React from 'react';
import type { Meta, StoryObj } from '@storybook/react-webpack5';
import { DSTabs } from './DSTabs';
import { User, Settings, Home, Bell } from 'lucide-react';

const meta: Meta<typeof DSTabs> = {
    title: 'Design/Tabs',
    component: DSTabs,
    parameters: { layout: 'centered' },
};

export default meta;
type Story = StoryObj<typeof DSTabs>;

const simpleTabs = [
    { id: 'tab1', label: 'General' },
    { id: 'tab2', label: 'Seguridad' },
    { id: 'tab3', label: 'Notificaciones' },
];

const tabsWithIcons = [
    { id: 'home', label: 'Inicio', icon: Home },
    { id: 'profile', label: 'Perfil', icon: User },
    { id: 'settings', label: 'Configuración', icon: Settings },
    { id: 'notifications', label: 'Alertas', icon: Bell },
];

export const Default: Story = {
    render: () => (
        <DSTabs tabs={simpleTabs}>
            <div className="p-4 text-sm text-[hsl(var(--text-secondary))]">
                Contenido de la pestaña General
            </div>
        </DSTabs>
    ),
};

export const WithIcons: Story = {
    render: () => (
        <DSTabs tabs={tabsWithIcons}>
            <div className="p-4 text-sm text-[hsl(var(--text-secondary))]">
                Contenido de la pestaña activa
            </div>
        </DSTabs>
    ),
};

export const WithDefaultTab: Story = {
    render: () => (
        <DSTabs tabs={simpleTabs} defaultTab="tab2">
            <div className="p-4 text-sm text-[hsl(var(--text-secondary))]">
                Contenido de Seguridad (default)
            </div>
        </DSTabs>
    ),
};

export const WithOnChange: Story = {
    render: () => (
        <DSTabs 
            tabs={simpleTabs} 
            onChange={(tabId) => console.log('Tab changed:', tabId)}
        >
            <div className="p-4 text-sm text-[hsl(var(--text-secondary))]">
                Cambia de pestaña para ver el evento en la consola
            </div>
        </DSTabs>
    ),
};

export const WithDisabledTab: Story = {
    render: () => (
        <DSTabs 
            tabs={[
                { id: 'tab1', label: 'Activo' },
                { id: 'tab2', label: 'Deshabilitado', disabled: true },
                { id: 'tab3', label: 'Otro Activo' },
            ]}
        >
            <div className="p-4 text-sm text-[hsl(var(--text-secondary))]">
                Contenido de la pestaña activa
            </div>
        </DSTabs>
    ),
};

export const FullExample: Story = {
    render: () => (
        <div className="w-96">
            <DSTabs tabs={tabsWithIcons} defaultTab="profile">
                <div className="space-y-4">
                    <h3 className="text-sm font-bold text-[hsl(var(--text-primary))]">
                        Configuración de Perfil
                    </h3>
                    <p className="text-xs text-[hsl(var(--text-secondary))]">
                        Administra tu información personal y preferencias de cuenta.
                    </p>
                    <div className="flex gap-2">
                        <button className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide bg-[hsl(var(--primary))] text-white rounded-md">
                            Guardar
                        </button>
                        <button className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide border border-white/20 text-white rounded-md">
                            Cancelar
                        </button>
                    </div>
                </div>
            </DSTabs>
        </div>
    ),
};
