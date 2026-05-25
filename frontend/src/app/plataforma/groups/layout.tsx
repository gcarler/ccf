"use client";

import React from 'react';
import { Home, MapPin, TrendingUp, History } from 'lucide-react';
import WorkspaceLayout from '@/components/WorkspaceLayout';

const GROUP_SECTIONS = [
    {
        id: 'overview',
        label: 'General',
        items: [
            { id: 'dashboard', label: 'Dashboard', icon: Home, href: '/groups' },
            { id: 'map', label: 'Mapa de Casas', icon: MapPin, href: '/groups/map' },
        ]
    },
    {
        id: 'analytics',
        label: 'Análisis',
        items: [
            { id: 'growth', label: 'Crecimiento', icon: TrendingUp, href: '/groups/analytics' },
            { id: 'history', label: 'Historial', icon: History, href: '/groups/history' },
        ]
    }
];

export default function GroupsLayout({ children }: { children: React.ReactNode }) {
    return (
        <WorkspaceLayout sidebarTitle="Casas de Bendición" sidebarSections={GROUP_SECTIONS} allowedPermissions={['community:read']}>
            {children}
        </WorkspaceLayout>
    );
}
