"use client";

import React from 'react';
import DashboardShell from '@/components/DashboardShell';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { LayoutDashboard, LucideIcon } from 'lucide-react';

interface ModulePageConfig {
    module: string;
    title: string;
    icon: LucideIcon;
}

const SIDEBAR_SECTIONS = [
    {
        title: 'Dashboards',
        items: [
            { id: 'dash-overview', label: 'Centro de Dashboards', href: '/plataforma/dashboard', icon: LayoutDashboard },
        ],
    },
];

export default function ModuleDashboardPage({ module, title, icon: Icon }: ModulePageConfig) {
    return (
        <WorkspaceLayout
            sidebarTitle="Dashboards"
            sidebarSections={SIDEBAR_SECTIONS}
        >
            <DashboardShell module={module} title={title} />
        </WorkspaceLayout>
    );
}
