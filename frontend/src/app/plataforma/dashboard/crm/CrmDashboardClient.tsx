"use client";

import React from 'react';
import DashboardShell from '@/components/DashboardShell';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { Users, LayoutDashboard } from 'lucide-react';

const SIDEBAR_SECTIONS = [
    { title: 'Dashboards', items: [
        { id: 'dash-overview', label: 'Centro de Dashboards', href: '/plataforma/dashboard', icon: LayoutDashboard },
        { id: 'dash-crm', label: 'CRM Pastoral', href: '/plataforma/dashboard/crm', icon: Users },
    ]},
];

export function CrmDashboardClient() {
    return (
        <WorkspaceLayout sidebarTitle="Dashboards" sidebarSections={SIDEBAR_SECTIONS}>
            <DashboardShell module="crm" title="CRM Pastoral" />
        </WorkspaceLayout>
    );
}
