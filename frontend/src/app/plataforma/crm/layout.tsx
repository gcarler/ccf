"use client";

import React from 'react';
import ProtectedRoute from '@/components/ProtectedRoute';

export default function CrmLayout({ children }: { children: React.ReactNode }) {
    return (
        <ProtectedRoute allowedPermissions={['crm:read']}>
            <div className="h-full w-full">
                {children}
            </div>
        </ProtectedRoute>
    );
}
