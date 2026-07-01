import React from 'react';
import type { Meta, StoryObj } from '@storybook/react-webpack5';
import { DSTooltip } from './DSTooltip';
import { DSButton } from './DSButton';

const meta: Meta<typeof DSTooltip> = {
    title: 'Design/Tooltip',
    component: DSTooltip,
    parameters: { layout: 'centered' },
    argTypes: {
        side: {
            control: 'select',
            options: ['top', 'right', 'bottom', 'left'],
        },
    },
};

export default meta;
type Story = StoryObj<typeof DSTooltip>;

export const Default: Story = {
    render: () => (
        <DSTooltip content="Este es un tooltip">
            <DSButton>Hover me</DSButton>
        </DSTooltip>
    ),
};

export const Top: Story = {
    render: () => (
        <DSTooltip content="Tooltip arriba" side="top">
            <DSButton>Top</DSButton>
        </DSTooltip>
    ),
};

export const Right: Story = {
    render: () => (
        <DSTooltip content="Tooltip a la derecha" side="right">
            <DSButton>Right</DSButton>
        </DSTooltip>
    ),
};

export const Bottom: Story = {
    render: () => (
        <DSTooltip content="Tooltip abajo" side="bottom">
            <DSButton>Bottom</DSButton>
        </DSTooltip>
    ),
};

export const Left: Story = {
    render: () => (
        <DSTooltip content="Tooltip a la izquierda" side="left">
            <DSButton>Left</DSButton>
        </DSTooltip>
    ),
};

export const AllPositions: Story = {
    render: () => (
        <div className="flex flex-col items-center gap-8">
            <DSTooltip content="Arriba" side="top">
                <DSButton>Top</DSButton>
            </DSTooltip>
            
            <div className="flex gap-8">
                <DSTooltip content="Izquierda" side="left">
                    <DSButton>Left</DSButton>
                </DSTooltip>
                
                <DSTooltip content="Centro" side="top">
                    <DSButton>Center</DSButton>
                </DSTooltip>
                
                <DSTooltip content="Derecha" side="right">
                    <DSButton>Right</DSButton>
                </DSTooltip>
            </div>
            
            <DSTooltip content="Abajo" side="bottom">
                <DSButton>Bottom</DSButton>
            </DSTooltip>
        </div>
    ),
};

export const WithIcon: Story = {
    render: () => (
        <DSTooltip content="Información" side="top">
            <button className="p-2 rounded-full bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-3))]">
                <svg className="size-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
            </button>
        </DSTooltip>
    ),
};

export const LongText: Story = {
    render: () => (
        <DSTooltip content="Este es un tooltip con texto largo para demostrar cómo se maneja el contenido extenso" side="top">
            <DSButton>Tooltip largo</DSButton>
        </DSTooltip>
    ),
};
