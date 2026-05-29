"use client";

import React from 'react';
import DashboardShell from '@/components/DashboardShell';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { Home, LayoutDashboard } from 'lucide-react';

const SIDEBAR_SECTIONS = [
    { title: 'Dashboards', items: [
        { id: 'dash-overview', label: 'Centro de Dashboards', href: '/plataforma/dashboard', icon: LayoutDashboard },
        { id: 'dash-evangelism', label: 'Evangelismo', href: '/plataforma/dashboard/evangelism', icon: Home },
    ]},
];

export function EvangelismDashboardClient() {
    return (
        <WorkspaceLayout sidebarTitle="Dashboards" sidebarSections={SIDEBAR_SECTIONS}>
            <DashboardShell module="evangelism" title="Evangelismo y Grupos" />
        </WorkspaceLayout>
    );
}
