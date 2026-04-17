"use client";

import React from 'react';
import { useRouter } from 'next/navigation';
import { BookOpen } from 'lucide-react';

/**
 * /wiki/docs — redirects to the wiki home which lists all documents.
 * This page exists to satisfy the route reference in WorkspaceLayout.
 */
export default function WikiDocsIndexPage() {
    const router = useRouter();

    // Redirect to wiki home on mount
    React.useEffect(() => {
        router.replace('/wiki');
    }, [router]);

    return (
        <div className="h-full flex items-center justify-center bg-slate-50 dark:bg-[#0f1117]">
            <div className="text-center space-y-3 opacity-50">
                <BookOpen size={32} className="mx-auto text-slate-300" />
                <p className="text-sm font-bold text-slate-400">Cargando Base de Conocimiento...</p>
            </div>
        </div>
    );
}

