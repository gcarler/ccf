"use client";

import React from 'react';
import DashboardShell from '@/components/DashboardShell';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { PiggyBank, LayoutDashboard } from 'lucide-react';

const SIDEBAR_SECTIONS = [
    { title: 'Dashboards', items: [
        { id: 'dash-overview', label: 'Centro de Dashboards', href: '/plataforma/dashboard', icon: LayoutDashboard },
        { id: 'dash-finance', label: 'Finanzas', href: '/plataforma/dashboard/finance', icon: PiggyBank },
    ]},
];

export function FinanceDashboardClient() {
    return (
        <WorkspaceLayout sidebarTitle="Dashboards" sidebarSections={SIDEBAR_SECTIONS}>
            <DashboardShell module="finance" title="Finanzas" />
        </WorkspaceLayout>
    );
}
