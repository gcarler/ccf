"use client";

import React from 'react';
import WorkspaceLayout from '@/components/WorkspaceLayout';

export default function TasksLayout({ children }: { children: React.ReactNode }) {
    return (
        <WorkspaceLayout>
            {children}
        </WorkspaceLayout>
    );
}
