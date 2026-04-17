"use client";

import React from 'react';
import { usePathname } from 'next/navigation';
import CrmShell from '@/components/crm/CrmShell';

export default function CrmLayout({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();
    
    // We can extract breadcrumbs or title from pathname here if needed
    // but CrmShell handles the base layout.
    
    return (
        <div className="h-full w-full">
            {children}
        </div>
    );
}
