import type { Meta, StoryObj } from '@storybook/react';
import React from 'react';
import {
    Home, Search, Settings, User, Bell, Mail, Lock, Plus, FileText,
    LayoutDashboard, Layout, List, Heart, Star, CheckCircle, AlertTriangle,
    Info, Calendar, Clock, MapPin, ArrowRight, ArrowLeft, ChevronDown,
    ChevronRight, X, Menu, Sun, Moon, Upload, Download, Trash2, Eye,
    BookOpen, Cross, Sparkles, Target, Quote, Users, Play, Award, Flag,
} from 'lucide-react';
import { DSMetric } from './components/DSMetric';
import { DSInput } from './components/DSInput';

const meta: Meta = {
    title: 'Design System/Iconos/Showcase',
    parameters: {
        docs: {
            description: {
                component: `
# Sistema de Iconos de CCF

El design system usa el tipo unificado \`AppIcon\` de \`@/types/icons\`
que acepta tanto iconos de Lucide como cualquier componente que reciba
\`size\` y \`className\`.

\`\`\`ts
export type AppIcon = LucideIcon | GenericIconComponent;

export type GenericIconComponent =
  React.ComponentType<{ size?: number | string; className?: string }>;
\`\`\`

**Componentes DS que aceptan \`AppIcon\`:**
- \`DSCommandEntry\` — icono de comando
- \`DSToolbarChip\` — chip de barra de herramientas
- \`DSInput\` — campo de entrada con icono
- \`DSMetric\` — tarjeta de métrica
- \`DSTabs\` — pestañas con iconos
- \`DSToast\` — notificación toast

> **Nota:** Los componentes solo renderizan el icono que reciben como prop.
> No existe un mapa global de iconos; cada componente importa los que necesita
> de \`lucide-react\` de forma explícita.
                `,
            },
        },
    },
    tags: ['autodocs'],
};

export default meta;

const iconList = [
    { name: 'Home', icon: Home },
    { name: 'Search', icon: Search },
    { name: 'Settings', icon: Settings },
    { name: 'User', icon: User },
    { name: 'Bell', icon: Bell },
    { name: 'Mail', icon: Mail },
    { name: 'Lock', icon: Lock },
    { name: 'Plus', icon: Plus },
    { name: 'Heart', icon: Heart },
    { name: 'Star', icon: Star },
    { name: 'CheckCircle', icon: CheckCircle },
    { name: 'AlertTriangle', icon: AlertTriangle },
    { name: 'Info', icon: Info },
    { name: 'Calendar', icon: Calendar },
    { name: 'Clock', icon: Clock },
    { name: 'MapPin', icon: MapPin },
    { name: 'FileText', icon: FileText },
    { name: 'LayoutDashboard', icon: LayoutDashboard },
    { name: 'Layout', icon: Layout },
    { name: 'List', icon: List },
    { name: 'Award', icon: Award },
    { name: 'Flag', icon: Flag },
    { name: 'Play', icon: Play },
    { name: 'ArrowRight', icon: ArrowRight },
    { name: 'ArrowLeft', icon: ArrowLeft },
    { name: 'ChevronDown', icon: ChevronDown },
    { name: 'ChevronRight', icon: ChevronRight },
    { name: 'X', icon: X },
    { name: 'Menu', icon: Menu },
    { name: 'Sun', icon: Sun },
    { name: 'Moon', icon: Moon },
    { name: 'Upload', icon: Upload },
    { name: 'Download', icon: Download },
    { name: 'Trash2', icon: Trash2 },
    { name: 'Eye', icon: Eye },
    { name: 'BookOpen', icon: BookOpen },
    { name: 'Cross', icon: Cross },
    { name: 'Sparkles', icon: Sparkles },
    { name: 'Target', icon: Target },
    { name: 'Quote', icon: Quote },
    { name: 'Users', icon: Users },
];

export const Grid: StoryObj = {
    render: () => (
        <div className="p-6 bg-[hsl(var(--bg-primary))]">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-4">
                Iconos disponibles en el design system ({iconList.length})
            </p>
            <div className="grid grid-cols-6 sm:grid-cols-8 md:grid-cols-10 gap-2">
                {iconList.map(({ name, icon: Icon }) => (
                    <div
                        key={name}
                        className="flex flex-col items-center gap-1.5 p-2 rounded-lg border border-[hsl(var(--border))] hover:border-[hsl(var(--primary))]/40 hover:bg-[hsl(var(--primary))]/5 transition-colors"
                    >
                        <Icon size={20} className="text-[hsl(var(--text-primary))]" />
                        <span className="text-[8px] font-mono text-[hsl(var(--text-secondary))] truncate w-full text-center">
                            {name}
                        </span>
                    </div>
                ))}
            </div>
        </div>
    ),
};

/** Muestra cómo se ven los iconos con diferentes tamaños */
export const Tamaños: StoryObj = {
    render: () => (
        <div className="p-6 bg-[hsl(var(--bg-primary))] space-y-4">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-2">
                Escala de tamaños con Home icon
            </p>
            <div className="flex items-end gap-4">
                {[12, 14, 16, 18, 20, 24, 28, 32, 40].map((size) => (
                    <div key={size} className="flex flex-col items-center gap-1">
                        <Home size={size} className="text-[hsl(var(--text-primary))]" />
                        <span className="text-[8px] font-mono text-[hsl(var(--text-secondary))]">{size}px</span>
                    </div>
                ))}
            </div>
        </div>
    ),
};

/** Muestra el uso del tipo AppIcon en los componentes DS reales */
export const UsoConComponentesDS: StoryObj = {
    render: () => (
        <div className="p-6 bg-[hsl(var(--bg-primary))] space-y-6">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-2">
                Componentes DS con iconos (vía AppIcon)
            </p>
            <div className="space-y-3">
                <div>
                    <p className="text-[9px] font-semibold text-[hsl(var(--text-secondary))] mb-1">DSMetric</p>
                    <div className="grid grid-cols-3 gap-2">
                        <DSMetric label="Miembros" value="1,234" icon={Users} tone="blue" />
                        <DSMetric label="Donaciones" value="$12K" icon={Heart} tone="emerald" />
                        <DSMetric label="Eventos" value="48" icon={Calendar} tone="amber" />
                    </div>
                </div>
                <div>
                    <p className="text-[9px] font-semibold text-[hsl(var(--text-secondary))] mb-1">DSInput</p>
                    <div className="flex gap-2">
                        <DSInput placeholder="Buscar..." icon={Search} />
                        <DSInput placeholder="correo@ejemplo.com" icon={Mail} />
                    </div>
                </div>
            </div>
        </div>
    ),
};
