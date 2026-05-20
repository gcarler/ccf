"use client";

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';

export default function HomeRoot() {
    const { isAuthenticated, loading } = useAuth();
    const router = useRouter();
    const [isMounted, setIsMounted] = useState(false);

    useEffect(() => {
        setIsMounted(true);
    }, []);

    useEffect(() => {
        if (!isMounted || loading) return;
        
        if (isAuthenticated) {
            router.replace('/mi-vista');
        } else {
            router.replace('/login');
        }
    }, [isAuthenticated, loading, isMounted, router]);

    // Prevent hydration mismatch
    if (!isMounted) {
        return <div className="h-screen w-full bg-[#f8fafc] dark:bg-[#0b0d11]" />;
    }

    return (
        <div className="h-screen w-full bg-[#f8fafc] dark:bg-[#0b0d11] flex flex-col items-center justify-center gap-4">
            <div className="relative">
                <div className="absolute inset-0 bg-blue-500/20 blur-xl rounded-full animate-pulse" />
                <Loader2 className="w-8 h-8 animate-spin text-blue-600 relative z-10" />
            </div>
            <p className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400">
                {isAuthenticated ? 'Abriendo ecosistema...' : 'Redirigiendo al Login...'}
            </p>
        </div>
    );
}
