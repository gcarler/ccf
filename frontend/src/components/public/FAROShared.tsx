"use client";

import React from 'react';
import Link from 'next/link';
import { Church } from 'lucide-react';
import { SITE_NAME } from "@/lib/site-config";

export function FAROHeader() {
    return (
        <nav className="fixed top-0 left-0 right-0 z-50 bg-white/80 dark:bg-[#1E1F21]/80 backdrop-blur-xl border-b border-slate-200/50 dark:border-white/5">
            <div className="container mx-auto px-4 py-2 flex items-center justify-between">
                <Link href="/" className="flex items-center gap-2">
                    <div className="bg-[hsl(var(--primary))] p-1.5 rounded-md">
                        <Church size={16} className="text-white" />
                    </div>
                    <span className="font-bold text-sm text-slate-900 dark:text-white">
                        {SITE_NAME}
                    </span>
                </Link>
            </div>
        </nav>
    );
}

export function FAROFooter() {
    return (
        <footer className="bg-slate-900 dark:bg-[#0f1117] text-white py-8 mt-auto">
            <div className="container mx-auto px-4 text-center text-sm text-slate-400">
                <p>{SITE_NAME} &copy; {new Date().getFullYear()}</p>
            </div>
        </footer>
    );
}
