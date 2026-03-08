"use client";

import React, { useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';

interface ProtectedRouteProps {
    children: React.ReactNode;
    allowedRoles?: string[];
}

export default function ProtectedRoute({ children, allowedRoles }: ProtectedRouteProps) {
    const { user, isAuthenticated, token } = useAuth();
    const router = useRouter();

    useEffect(() => {
        // If not authenticated and no token in localStorage, redirect to login
        const savedToken = localStorage.getItem('ccf_token');
        if (!isAuthenticated && !savedToken) {
            router.push('/login');
        }
    }, [isAuthenticated, router]);

    // If roles are specified, check if user has one of them
    useEffect(() => {
        if (user && allowedRoles && !allowedRoles.includes(user.role)) {
            // Redirect to appropriate page based on role if they try to access unauthorized area
            if (user.role === 'admin' || user.role === 'coordinador' || user.role === 'docente') {
                router.push('/admin');
            } else {
                router.push('/academy');
            }
        }
    }, [user, allowedRoles, router]);

    if (!isAuthenticated || (allowedRoles && user && !allowedRoles.includes(user.role))) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950">
                <Loader2 className="w-12 h-12 animate-spin text-primary" />
            </div>
        );
    }

    return <>{children}</>;
}
