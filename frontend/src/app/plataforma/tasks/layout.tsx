"use client";

import React from 'react';
import ProtectedRoute from '@/components/ProtectedRoute';

export default function TasksLayout({ children }: { children: React.ReactNode }) {
    return (
        <ProtectedRoute allowedPermissions={['projects:read']}>
            {children}
        </ProtectedRoute>
    );
}

