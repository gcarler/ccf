"use client";

import React from 'react';
import DashboardShell from '@/components/DashboardShell';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { Calendar, LayoutDashboard } from 'lucide-react';

const SIDEBAR_SECTIONS = [
    { title: 'Dashboards', items: [
        { id: 'dash-overview', label: 'Centro de Dashboards', href: '/plataforma/dashboard', icon: LayoutDashboard },
        { id: 'dash-agenda', label: 'Agenda', href: '/plataforma/dashboard/agenda', icon: Calendar },
    ]},
];

export function AgendaDashboardClient() {
    return (
        <WorkspaceLayout sidebarTitle="Dashboards" sidebarSections={SIDEBAR_SECTIONS}>
            <DashboardShell module="agenda" title="Agenda y Eventos" />
        </WorkspaceLayout>
    );
}
