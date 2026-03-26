"use client";

import React from 'react';

export default function CmsLayout({ children }: { children: React.ReactNode }) {
    return <div className="min-h-screen bg-[#f8f9fb] dark:bg-[#0f1012] text-slate-900 dark:text-white">{children}</div>;
}
