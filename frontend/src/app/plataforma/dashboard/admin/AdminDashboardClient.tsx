"use client";

import React from 'react';
import DashboardShell from '@/components/DashboardShell';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { Shield, LayoutDashboard } from 'lucide-react';

const SIDEBAR_SECTIONS = [
    { title: 'Dashboards', items: [
        { id: 'dash-overview', label: 'Centro de Dashboards', href: '/plataforma/dashboard', icon: LayoutDashboard },
        { id: 'dash-admin', label: 'Admin', href: '/plataforma/dashboard/admin', icon: Shield },
    ]},
];

export function AdminDashboardClient() {
    return (
        <WorkspaceLayout sidebarTitle="Dashboards" sidebarSections={SIDEBAR_SECTIONS}>
            <DashboardShell module="admin" title="Panel de Administración" />
        </WorkspaceLayout>
    );
}
