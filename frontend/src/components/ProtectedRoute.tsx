"use client";

import React, { useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/navigation';

interface ProtectedRouteProps {
    children: React.ReactNode;
    allowedRoles?: string[];
    requireVerifiedEmail?: boolean;
}

export default function ProtectedRoute({ children, allowedRoles }: ProtectedRouteProps) {
    const { user, isAuthenticated, loading } = useAuth();
    const router = useRouter();

    useEffect(() => {
        // QUALITY LOG: Trace why a redirect might happen
        const hasToken = typeof window !== 'undefined' && !!localStorage.getItem('ccf_token');
        
        if (!loading) {
            if (!isAuthenticated && !hasToken) {
                console.warn("[AUTH QUALITY] No user and no token found. Redirecting to login.");
                router.push('/login');
            } else if (isAuthenticated && allowedRoles && user) {
                const normalizedUserRole = user.role.toLowerCase();
                const normalizedAllowedRoles = allowedRoles.map(r => r.toLowerCase());
                
                if (!normalizedAllowedRoles.includes(normalizedUserRole)) {
                    console.warn(`[AUTH QUALITY] Role mismatch: ${normalizedUserRole} not in ${normalizedAllowedRoles}. Redirecting to dashboard.`);
                    if (['admin', 'coordinador', 'docente'].includes(normalizedUserRole)) {
                        router.push('/admin');
                    } else {
                        router.push('/academy');
                    }
                }
            }
        }
    }, [isAuthenticated, loading, user, allowedRoles, router]);

    if (loading) {
        return (
            <div className="flex h-screen w-full items-center justify-center bg-slate-50 dark:bg-[#111213]">
                <div className="flex flex-col items-center gap-4">
                    <div className="h-12 w-12 animate-spin rounded-full border-4 border-blue-600 border-t-transparent"></div>
                    <p className="text-sm font-bold text-slate-500 animate-pulse uppercase tracking-widest">Verificando Credenciales...</p>
                </div>
            </div>
        );
    }

    if (!isAuthenticated) {
        return null;
    }

    if (allowedRoles && user && !allowedRoles.includes(user.role)) {
        return null;
    }

    return <>{children}</>;
}
