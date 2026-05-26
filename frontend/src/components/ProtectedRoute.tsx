"use client";

import React, { useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/navigation';

interface ProtectedRouteProps {
    children: React.ReactNode;
    allowedRoles?: string[];
    allowedPermissions?: string[];
    requireVerifiedEmail?: boolean;
}

export default function ProtectedRoute({ children, allowedRoles, allowedPermissions }: ProtectedRouteProps) {
    const { user, isAuthenticated, loading, hasPermission } = useAuth();
    const router = useRouter();

    useEffect(() => {
        // QUALITY LOG: Trace why a redirect might happen
        const hasToken = typeof window !== 'undefined' && !!localStorage.getItem('ccf_token');

        if (!loading) {
            if (!isAuthenticated && !hasToken) {
                console.warn("[AUTH QUALITY] No user and no token found. Redirecting to login.");
                router.push('/login');
            } else if (isAuthenticated && user) {
                if (allowedRoles) {
                    const normalizedUserRole = user.role.toLowerCase();
                    const normalizedAllowedRoles = allowedRoles.map(r => r.toLowerCase());

                    if (!normalizedAllowedRoles.includes(normalizedUserRole)) {
                        console.warn(`[AUTH QUALITY] Role mismatch: ${normalizedUserRole} not in ${normalizedAllowedRoles}. Redirecting to dashboard.`);
                        if (['admin', 'coordinador', 'docente'].includes(normalizedUserRole)) {
                            router.push('/plataforma/admin');
                        } else {
                            router.push('/plataforma/academy');
                        }
                        return;
                    }
                }
                if (allowedPermissions) {
                    const hasAny = allowedPermissions.some(p => hasPermission(p));
                    if (!hasAny) {
                        console.warn(`[AUTH QUALITY] No required permissions ${allowedPermissions}. Redirecting.`);
                        router.push('/plataforma/academy');
                    }
                }
            }
        }
    }, [isAuthenticated, loading, user, allowedRoles, allowedPermissions, hasPermission, router]);

    if (loading) {
        return (
            <div className="flex h-screen w-full items-center justify-center bg-slate-50 dark:bg-[#111213]">
                <div className="flex flex-col items-center gap-4">
                    <div className="h-8 w-12 animate-spin rounded-full border-4 border-blue-600 border-t-transparent"></div>
                    <p className="text-sm font-bold text-slate-500 animate-pulse uppercase tracking-wide">Verificando Credenciales...</p>
                </div>
            </div>
        );
    }

    if (!isAuthenticated) {
        return (
            <div className="flex h-screen w-full items-center justify-center bg-slate-50 dark:bg-[#111213]">
                <div className="flex flex-col items-center gap-4 max-w-md text-center px-6">
                    <div className="w-16 h-16 rounded-full bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
                        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#d97706" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                            <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
                        </svg>
                    </div>
                    <h2 className="text-xl font-extrabold text-slate-800 dark:text-white">Acceso Restringido</h2>
                    <p className="text-sm text-slate-500 dark:text-slate-400">Debes iniciar sesión para acceder a esta sección.</p>
                    <a href="/login" className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs uppercase tracking-wider px-6 py-3 rounded-xl transition-all no-underline">
                        Ir al Login
                    </a>
                </div>
            </div>
        );
    }

    if (allowedRoles && user && !allowedRoles.includes(user.role)) {
        return (
            <div className="flex h-screen w-full items-center justify-center bg-slate-50 dark:bg-[#111213]">
                <div className="flex flex-col items-center gap-4 max-w-md text-center px-6">
                    <div className="w-16 h-16 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
                        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#dc2626" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <circle cx="12" cy="12" r="10"/>
                            <line x1="15" y1="9" x2="9" y2="15"/>
                            <line x1="9" y1="9" x2="15" y2="15"/>
                        </svg>
                    </div>
                    <h2 className="text-xl font-extrabold text-slate-800 dark:text-white">Sin Permisos</h2>
                    <p className="text-sm text-slate-500 dark:text-slate-400">Este módulo requiere rol pastoral o administrativo.</p>
                    <a href="/plataforma/admin" className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs uppercase tracking-wider px-6 py-3 rounded-xl transition-all no-underline">
                        Volver al Inicio
                    </a>
                </div>
            </div>
        );
    }

    if (allowedPermissions && user && !allowedPermissions.some(p => hasPermission(p))) {
        return (
            <div className="flex h-screen w-full items-center justify-center bg-slate-50 dark:bg-[#111213]">
                <div className="flex flex-col items-center gap-4 max-w-md text-center px-6">
                    <div className="w-16 h-16 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
                        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#dc2626" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <circle cx="12" cy="12" r="10"/>
                            <line x1="15" y1="9" x2="9" y2="15"/>
                            <line x1="9" y1="9" x2="15" y2="15"/>
                        </svg>
                    </div>
                    <h2 className="text-xl font-extrabold text-slate-800 dark:text-white">Permiso Denegado</h2>
                    <p className="text-sm text-slate-500 dark:text-slate-400">No tienes los permisos necesarios para acceder a esta sección.</p>
                    <a href="/plataforma/admin" className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs uppercase tracking-wider px-6 py-3 rounded-xl transition-all no-underline">
                        Volver al Inicio
                    </a>
                </div>
            </div>
        );
    }

    return <>{children}</>;
}
