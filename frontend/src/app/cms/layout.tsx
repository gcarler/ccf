"use client";

import React from 'react';
import WorkspaceLayout from '@/components/WorkspaceLayout';

export default function CmsLayout({ children }: { children: React.ReactNode }) {
    return (
        <WorkspaceLayout>
            {children}
        </WorkspaceLayout>
    );
}
