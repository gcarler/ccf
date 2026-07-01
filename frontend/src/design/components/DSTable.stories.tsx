import React from 'react';
import type { Meta, StoryObj } from '@storybook/react-webpack5';
import { DSTable } from './DSTable';
import { ColumnDef } from '@tanstack/react-table';

interface User {
    id: string;
    name: string;
    email: string;
    role: string;
    status: 'active' | 'inactive';
}

const columns: ColumnDef<User, any>[] = [
    { accessorKey: 'name', header: 'Nombre' },
    { accessorKey: 'email', header: 'Email' },
    { accessorKey: 'role', header: 'Rol' },
    { 
        accessorKey: 'status', 
        header: 'Estado',
        cell: ({ getValue }) => (
            <span className={`px-2 py-0.5 rounded-full text-[9px] font-semibold uppercase ${
                getValue() === 'active' 
                    ? 'bg-emerald-500/15 text-emerald-400' 
                    : 'bg-slate-500/15 text-slate-400'
            }`}>
                {getValue() === 'active' ? 'Activo' : 'Inactivo'}
            </span>
        ),
    },
];

const sampleData: User[] = [
    { id: '1', name: 'Juan Pérez', email: 'juan@ejemplo.com', role: 'Admin', status: 'active' },
    { id: '2', name: 'María García', email: 'maria@ejemplo.com', role: 'Usuario', status: 'active' },
    { id: '3', name: 'Carlos López', email: 'carlos@ejemplo.com', role: 'Visor', status: 'inactive' },
    { id: '4', name: 'Ana Martínez', email: 'ana@ejemplo.com', role: 'Usuario', status: 'active' },
];

const meta: Meta<typeof DSTable> = {
    title: 'Design/Table',
    component: DSTable,
    parameters: { layout: 'centered' },
    argTypes: {
        sortable: { control: 'boolean' },
        compact: { control: 'boolean' },
    },
};

export default meta;
type Story = StoryObj<typeof DSTable>;

export const Default: Story = {
    args: {
        data: sampleData,
        columns: columns as any,
    },
};

export const WithoutSorting: Story = {
    args: {
        data: sampleData,
        columns: columns as any,
        sortable: false,
    },
};

export const Compact: Story = {
    args: {
        data: sampleData,
        columns: columns as any,
        compact: true,
    },
};

export const Empty: Story = {
    args: {
        data: [],
        columns: columns as any,
        emptyMessage: 'No hay usuarios registrados',
    },
};

export const WithRowClick: Story = {
    args: {
        data: sampleData,
        columns: columns as any,
        onRowClick: (row: any) => console.log('Row clicked:', row),
    },
};

export const ManyRows: Story = {
    args: {
        data: Array.from({ length: 20 }, (_, i) => ({
            id: String(i + 1),
            name: `Usuario ${i + 1}`,
            email: `usuario${i + 1}@ejemplo.com`,
            role: i % 3 === 0 ? 'Admin' : i % 3 === 1 ? 'Usuario' : 'Visor',
            status: i % 2 === 0 ? ('active' as const) : ('inactive' as const),
        })),
        columns: columns as any,
    },
};
