"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { apiFetch } from '@/lib/http';

interface AuthContextType {
    user: any;
    token: string | null;
    login: (accessToken?: string, refreshToken?: string) => Promise<void>;
    logout: () => void;
    refresh: () => Promise<void>;
    isAuthenticated: boolean;
    loading: boolean;
    hasModuleAccess: (module: string, minLevel?: string) => boolean;
    hasPermission: (perm: string) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [token, setToken] = useState<string | null>(null);
    const [user, setUser] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const router = useRouter();

    const redirectByRole = useCallback((role: string) => {
        const r = role.toLowerCase();
        if (r === 'admin' || r === 'pastor') router.push('/plataforma/admin');
        else if (r === 'profesor') router.push('/plataforma/academy');
        else router.push('/plataforma/crm');
    }, [router]);

    const logout = useCallback(() => {
        apiFetch('/auth/logout', { method: 'POST' }).catch(() => {});
        if (typeof window !== 'undefined') {
            sessionStorage.removeItem('ccf_token');
            sessionStorage.removeItem('ccf_refresh_token');
        }
        setToken(null);
        setUser(null);
        window.location.href = '/login';
    }, []);

    const fetchUser = useCallback(async (tokenValue?: string) => {
        const t = tokenValue || (typeof window !== 'undefined' ? sessionStorage.getItem('ccf_token') : null);
        if (!t) { setLoading(false); return null; }

        const timer = setTimeout(() => { console.warn('[AUTH] timeout'); setLoading(false); }, 6000);
        try {
            // Try v3 auth first (UUID-based), fallback to v1
            let data: any = null;
            let v3Data: any = null;
            try {
                v3Data = await apiFetch<any>('/v3/auth/me', { cache: 'no-store', token: t });
            } catch { /* fallback to v1 */ }
            
            if (v3Data && v3Data.user_id) {
                // Map v3 response to v1-compatible shape
                data = {
                    id: v3Data.user_id,
                    username: v3Data.username || v3Data.email?.split('@')[0],
                    email: v3Data.email,
                    role: (v3Data.platform_role || 'LECTOR').toLowerCase(),
                    is_active: true,
                    is_email_verified: v3Data.is_verified || false,
                    xp: 0,
                    created_at: new Date().toISOString(),
                    permissions: v3Data.permissions || {},
                };
            } else {
                data = await apiFetch<any>('/auth/me', { cache: 'no-store', token: t });
                if (!data.permissions) {
                    try {
                        const p = await apiFetch<any>('/auth/me/permissions', { cache: 'no-store', token: t });
                        data.permissions = p.permissions || {};
                    } catch { data.permissions = {}; }
                }
            }
            setUser(data);
            setToken(t);
            if (tokenValue && typeof window !== 'undefined') sessionStorage.setItem('ccf_token', tokenValue);
            return data;
        } catch (err: any) {
            if (err?.status === 401) {
                if (typeof window !== 'undefined') {
                    sessionStorage.removeItem('ccf_token');
                    sessionStorage.removeItem('ccf_refresh_token');
                }
                setUser(null);
                setToken(null);
                window.location.href = '/login?expired=1';
            }
            return null;
        } finally { clearTimeout(timer); setLoading(false); }
    }, []);

    useEffect(() => { fetchUser(); }, []); // only on mount

    const login = useCallback(async (accessToken?: string, refreshToken?: string) => {
        if (accessToken && typeof window !== 'undefined') {
            sessionStorage.setItem('ccf_token', accessToken);
            setToken(accessToken);
        }
        if (refreshToken && typeof window !== 'undefined') {
            sessionStorage.setItem('ccf_refresh_token', refreshToken);
        }
        const data = await fetchUser(accessToken);
        if (data?.role) redirectByRole(data.role);
        else if (accessToken) router.push('/plataforma/admin');
        
        // Auto-refresh permissions cache
        try {
            if (accessToken) {
                await apiFetch('/v3/auth/me', { token: accessToken, silent: true });
            }
        } catch { /* silent */ }
    }, [fetchUser, redirectByRole, router]);

    const refresh = useCallback(async () => { await fetchUser(); }, [fetchUser]);

    const hasModuleAccess = (module: string, minLevel = 'read') => {
        if (!user?.permissions) return false;
        if (user.role === 'admin') return true;
        const k = `${module}:${minLevel}`;
        if (user.permissions[k] === 'allow') return true;
        if (minLevel === 'read' && (user.permissions[`${module}:edit`] === 'allow' || user.permissions[`${module}:manage`] === 'allow')) return true;
        if (minLevel === 'edit' && user.permissions[`${module}:manage`] === 'allow') return true;
        return false;
    };

    const hasPermission = (perm: string) => {
        if (!user?.permissions) return false;
        if (user.role === 'admin') return true;
        return user.permissions[perm] === 'allow';
    };

    return (
        <AuthContext.Provider value={{ user, token, login, logout, refresh, isAuthenticated: !!token, loading, hasModuleAccess, hasPermission }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const ctx = useContext(AuthContext);
    if (ctx === undefined) throw new Error('useAuth must be used within AuthProvider');
    return ctx;
}
