"use client";

import React from 'react';
import { Home, MapPin, TrendingUp, History } from 'lucide-react';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { ModuleErrorBoundary } from '@/components/ModuleErrorBoundary';

const GROUP_SECTIONS = [
    {
        id: 'overview',
        label: 'General',
        items: [
            { id: 'dashboard', label: 'Dashboard', icon: Home, href: '/plataforma/community/grupos' },
            { id: 'map', label: 'Mapa de Casas', icon: MapPin, href: '/plataforma/groups/map' },
        ]
    },
    {
        id: 'analytics',
        label: 'Análisis',
        items: [
            { id: 'growth', label: 'Crecimiento', icon: TrendingUp, href: '/plataforma/groups/analytics' },
            { id: 'history', label: 'Historial', icon: History, href: '/plataforma/groups/history' },
        ]
    }
];

export default function GroupsLayout({ children }: { children: React.ReactNode }) {
    return (
        <ModuleErrorBoundary moduleName="Grupos">
            <WorkspaceLayout sidebarTitle="Grupos" sidebarSections={GROUP_SECTIONS} allowedPermissions={['community:read']}>
                {children}
            </WorkspaceLayout>
        </ModuleErrorBoundary>
    );
}
