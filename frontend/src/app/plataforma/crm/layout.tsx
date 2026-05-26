"use client";

import React from 'react';
import ProtectedRoute from '@/components/ProtectedRoute';
import { ModuleErrorBoundary } from '@/components/ModuleErrorBoundary';

export default function CrmLayout({ children }: { children: React.ReactNode }) {
    return (
        <ProtectedRoute allowedPermissions={['crm:read']}>
            <ModuleErrorBoundary moduleName="CRM">
                <div className="h-full w-full">
                    {children}
                </div>
            </ModuleErrorBoundary>
        </ProtectedRoute>
    );
}
