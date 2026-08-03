"use client";

import React from 'react';
import DashboardShell from '@/components/DashboardShell';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { FolderKanban, LayoutDashboard } from 'lucide-react';
import { PROJECTS_LIST_ROUTE } from '@/app/plataforma/projects/projectsLinks';

const SIDEBAR_SECTIONS = [
    { title: 'Dashboards', items: [
        { id: 'dash-overview', label: 'Centro de Dashboards', href: '/plataforma/dashboard', icon: LayoutDashboard },
        { id: 'dash-projects', label: 'Proyectos', href: PROJECTS_LIST_ROUTE, icon: FolderKanban },
    ]},
];

export function ProjectsDashboardClient() {
    return (
        <WorkspaceLayout sidebarTitle="Dashboards" sidebarSections={SIDEBAR_SECTIONS}>
            <DashboardShell module="projects" title="Proyectos" />
        </WorkspaceLayout>
    );
}
