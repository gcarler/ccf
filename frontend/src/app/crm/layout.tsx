"use client";

import React from 'react';

export default function CrmLayout({ children }: { children: React.ReactNode }) {
    return (
        <div className="h-full w-full">
            {children}
        </div>
    );
}
