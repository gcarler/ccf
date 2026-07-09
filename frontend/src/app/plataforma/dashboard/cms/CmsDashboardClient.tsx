"use client";

import React from 'react';
import DashboardShell from '@/components/DashboardShell';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { FileText, LayoutDashboard } from 'lucide-react';

const SIDEBAR_SECTIONS = [
    { title: 'Dashboards', items: [
        { id: 'dash-overview', label: 'Centro de Dashboards', href: '/plataforma/dashboard', icon: LayoutDashboard },
        { id: 'dash-cms', label: 'CMS', href: '/plataforma/dashboard/cms', icon: FileText },
    ]},
];

// The "SEO score trend" widget is rendered by ``DashboardShell`` itself
// when ``data.seo_trend.has_data`` is true. This keeps the widget
// data-driven (no duplicate fetch) and keeps the client component thin.
// See: components/DashboardShell → SeoTrendCard.
export function CmsDashboardClient() {
    return (
        <WorkspaceLayout sidebarTitle="Dashboards" sidebarSections={SIDEBAR_SECTIONS}>
            <DashboardShell module="cms" title="Gestión de Contenido (CMS)" />
        </WorkspaceLayout>
    );
}

