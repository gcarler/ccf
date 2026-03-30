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
    const [token, setToken] = useState<string | null>(() => {
        if (typeof window !== 'undefined') return localStorage.getItem('ccf_token');
        return null;
    });
    const [user, setUser] = useState<AuthContextType["user"]>(null);
    const [loading, setLoading] = useState(true);
    const router = useRouter();

    const redirectByRole = useCallback((role: string) => {
        const normalizedRole = role.toLowerCase();
        if (["admin", "coordinador", "docente"].includes(normalizedRole)) {
            router.push('/admin');
            return;
        }
        router.push('/academy');
    }, [router]);

    const logout = useCallback(() => {
        void apiFetch('/auth/logout', { method: 'POST' }).catch(() => {});
        if (typeof window !== 'undefined') localStorage.removeItem('ccf_token');
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
            console.error('[AUTH QUALITY] Error fetching user profile:', error);
            // Only clear session if it's strictly a 401/Invalid Token
            if ((error as any).status === 401) {
                if (typeof window !== 'undefined') localStorage.removeItem('ccf_token');
                setUser(null);
                setToken(null);
            }
            return null;
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchUser();
    }, [fetchUser]);

    const login = useCallback(async (accessToken?: string) => {
        setLoading(true);
        if (accessToken && typeof window !== 'undefined') {
            localStorage.setItem('ccf_token', accessToken);
            setToken(accessToken);
        }
        const userData = await fetchUser(accessToken);
        if (userData?.role) {
            redirectByRole(userData.role);
        } else if (accessToken) {
            // Success login but profile fetch pending/failed - Force entry anyway
            console.warn("[AUTH QUALITY] Login success but profile fetch failed. Forcing entry to admin.");
            router.push('/admin');
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
