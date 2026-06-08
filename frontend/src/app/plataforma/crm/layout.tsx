"use client";

import React from 'react';
import ProtectedRoute from '@/components/ProtectedRoute';
import { ModuleErrorBoundary } from '@/components/ModuleErrorBoundary';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { CRM_SIDEBAR_SECTIONS } from '@/components/crm/sidebarConfig';

export default function CrmLayout({ children }: { children: React.ReactNode }) {
    return (
        <ProtectedRoute allowedPermissions={['crm:read', 'crm:edit', 'crm:manage']}>
            <ModuleErrorBoundary moduleName="CRM">
                <WorkspaceLayout
                    sidebarTitle="CRM Pastoral"
                    sidebarSections={CRM_SIDEBAR_SECTIONS}
                >
                    <div className="bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] h-full">
                        {children}
                    </div>
                </WorkspaceLayout>
            </ModuleErrorBoundary>
        </ProtectedRoute>
    );
}
