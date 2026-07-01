import React, { useState } from 'react';
import type { Meta, StoryObj } from '@storybook/react-webpack5';
import { DSModal } from './DSModal';
import { DSButton } from './DSButton';

const meta: Meta<typeof DSModal> = {
    title: 'Design/Modal',
    component: DSModal,
    parameters: { layout: 'centered' },
    argTypes: {
        size: {
            control: 'select',
            options: ['sm', 'md', 'lg'],
        },
        showClose: { control: 'boolean' },
    },
};

export default meta;
type Story = StoryObj<typeof DSModal>;

const ModalWithState = (props: any) => {
    const [open, setOpen] = useState(false);
    return (
        <>
            <DSButton onClick={() => setOpen(true)}>Abrir Modal</DSButton>
            <DSModal {...props} open={open} onClose={() => setOpen(false)} />
        </>
    );
};

export const Default: Story = {
    render: () => (
        <ModalWithState title="Modal de Ejemplo">
            <p className="text-sm text-[hsl(var(--text-secondary))]">
                Este es un modal de ejemplo con contenido básico.
            </p>
        </ModalWithState>
    ),
};

export const Small: Story = {
    render: () => (
        <ModalWithState title="Modal Pequeño" size="sm">
            <p className="text-sm text-[hsl(var(--text-secondary))]">
                Modal pequeño para confirmaciones rápidas.
            </p>
        </ModalWithState>
    ),
};

export const Large: Story = {
    render: () => (
        <ModalWithState title="Modal Grande" size="lg">
            <div className="space-y-3">
                <p className="text-sm text-[hsl(var(--text-secondary))]">
                    Modal grande para contenido extenso como formularios o listas.
                </p>
                <div className="p-3 bg-[hsl(var(--surface-2))] rounded-lg">
                    <p className="text-xs text-[hsl(var(--text-secondary))]">
                        Contenido adicional aquí...
                    </p>
                </div>
            </div>
        </ModalWithState>
    ),
};

export const WithoutCloseButton: Story = {
    render: () => (
        <ModalWithState title="Sin Botón Cerrar" showClose={false}>
            <p className="text-sm text-[hsl(var(--text-secondary))]">
                Este modal no tiene botón de cerrar. Solo se puede cerrar con Escape o haciendo clic fuera.
            </p>
        </ModalWithState>
    ),
};

export const WithForm: Story = {
    render: () => (
        <ModalWithState title="Crear Usuario" size="md">
            <div className="space-y-3">
                <div>
                    <label className="block text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1">
                        Nombre
                    </label>
                    <input 
                        type="text" 
                        className="w-full px-2.5 py-1.5 text-xs bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border))] rounded-md"
                        placeholder="Nombre completo"
                    />
                </div>
                <div>
                    <label className="block text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1">
                        Email
                    </label>
                    <input 
                        type="email" 
                        className="w-full px-2.5 py-1.5 text-xs bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border))] rounded-md"
                        placeholder="correo@ejemplo.com"
                    />
                </div>
                <div className="flex justify-end gap-2 pt-2">
                    <DSButton variant="ghost">Cancelar</DSButton>
                    <DSButton>Guardar</DSButton>
                </div>
            </div>
        </ModalWithState>
    ),
};

export const ConfirmationDialog: Story = {
    render: () => (
        <ModalWithState title="Confirmar Eliminación" size="sm">
            <div className="space-y-3">
                <p className="text-sm text-[hsl(var(--text-secondary))]">
                    ¿Estás seguro de que deseas eliminar este elemento? Esta acción no se puede deshacer.
                </p>
                <div className="flex justify-end gap-2">
                    <DSButton variant="ghost">Cancelar</DSButton>
                    <DSButton variant="primary">Eliminar</DSButton>
                </div>
            </div>
        </ModalWithState>
    ),
};
