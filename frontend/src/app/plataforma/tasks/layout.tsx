"use client";

import React from 'react';
import ProtectedRoute from '@/components/ProtectedRoute';
import { ModuleErrorBoundary } from '@/components/ModuleErrorBoundary';

export default function TasksLayout({ children }: { children: React.ReactNode }) {
    return (
        <ProtectedRoute allowedPermissions={['projects:read']}>
            <ModuleErrorBoundary moduleName="Tareas">
                {children}
            </ModuleErrorBoundary>
        </ProtectedRoute>
    );
}

