"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { apiFetch } from '@/lib/http';

interface AuthContextType {
    user: {
        id: number;
        username: string;
        email: string;
        role: string;
        is_email_verified?: boolean;
    } | null;
    token: string | null;
    login: (token?: string, refreshToken?: string) => Promise<void>;
    logout: () => void;
    refresh: () => Promise<void>;
    isAuthenticated: boolean;
    loading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
    // Always start with null for SSR/client consistency (prevents hydration mismatch).
    // The actual token is read from localStorage inside useEffect (client-only).
    const [token, setToken] = useState<string | null>(null);
    const [user, setUser] = useState<AuthContextType["user"]>(null);
    const [loading, setLoading] = useState(true);
    const router = useRouter();

    const redirectByRole = useCallback((role: string) => {
        const normalizedRole = role.toLowerCase();
        if (["admin", "coordinador", "docente"].includes(normalizedRole)) {
            router.push('/plataforma/admin');
            return;
        }
        router.push('/plataforma/academy');
    }, [router]);

    const logout = useCallback(() => {
        void apiFetch('/auth/logout', { method: 'POST' }).catch(() => {});
        if (typeof window !== 'undefined') {
            localStorage.removeItem('ccf_token');
            localStorage.removeItem('ccf_refresh_token');
        }
        setToken(null);
        setUser(null);
        router.push('/login');
    }, [router]);

    const fetchUser = useCallback(async (tokenValue?: string) => {
        const activeToken = tokenValue || (typeof window !== 'undefined' ? localStorage.getItem('ccf_token') : null);

        if (!activeToken) {
            setLoading(false);
            return null;
        }

        // Safety net: if anything hangs (backend down), resolve loading after 6s
        const safetyTimer = setTimeout(() => {
            console.warn('[AUTH] fetchUser timeout — forcing loading=false');
            setLoading(false);
        }, 6000);

        try {
            const userData = await apiFetch<any>('/auth/me', {
                cache: 'no-store',
                token: activeToken
            });
            setUser(userData);
            setToken(activeToken);
            if (typeof window !== 'undefined' && tokenValue) {
                localStorage.setItem('ccf_token', tokenValue);
            }
            return userData;
        } catch (error) {
            console.error('[AUTH] Error fetching user profile:', error);
            // Only clear session on explicit 401 (not network errors)
            const status = (error as any).status;
            if (status === 401) {
                if (typeof window !== 'undefined') localStorage.removeItem('ccf_token');
                setUser(null);
                setToken(null);
            }
            // For status === 0 (network error/timeout): keep the token,
            // don't log out — the user may just be offline temporarily.
            return null;
        } finally {
            clearTimeout(safetyTimer);
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchUser();
    }, [fetchUser]);

    const login = useCallback(async (accessToken?: string, refreshToken?: string) => {
        setLoading(true);
        if (accessToken && typeof window !== 'undefined') {
            localStorage.setItem('ccf_token', accessToken);
            setToken(accessToken);
        }
        if (refreshToken && typeof window !== 'undefined') {
            localStorage.setItem('ccf_refresh_token', refreshToken);
        }
        const userData = await fetchUser(accessToken);
        if (userData?.role) {
            redirectByRole(userData.role);
        } else if (accessToken) {
            // Success login but profile fetch pending/failed - Force entry anyway
            console.warn("[AUTH QUALITY] Login success but profile fetch failed. Forcing entry to admin.");
            router.push('/plataforma/admin');
        }
    }, [fetchUser, redirectByRole, router]);

    const refresh = useCallback(async () => {
        await fetchUser();
    }, [fetchUser]);

    return (
        <AuthContext.Provider value={{ user, token, login, logout, refresh, isAuthenticated: !!token, loading }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}
