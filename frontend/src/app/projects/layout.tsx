"use client";

import React from 'react';
import ProtectedRoute from '@/components/ProtectedRoute';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { usePathname } from 'next/navigation';

export default function ProjectsLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const pathname = usePathname();

    const getSidebarTitle = () => {
        if (!pathname || pathname === '/projects') return 'Proyectos';
        const segments = pathname.split('/');
        const last = segments[segments.length - 1];
        return `Proyectos / ${last.charAt(0).toUpperCase() + last.slice(1)}`;
    };

    const dummySections = [
        { label: 'Placeholder' } // Minimal required to trigger length > 0
    ];

    return (
        <ProtectedRoute>
            <WorkspaceLayout sidebarTitle={getSidebarTitle()} sidebarSections={dummySections}>
                <div className="bg-[#f8f9fb] dark:bg-[#141517] min-h-screen">
                    {children}
                </div>
            </WorkspaceLayout>
        </ProtectedRoute>
    );
}
