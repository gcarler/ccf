"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { apiFetch } from '@/lib/http';
import { useAuthStore } from '@/stores/authStore';

interface AuthContextType {
    user: {
        id: number;
        username: string;
        email: string;
        role: string;
        is_email_verified?: boolean;
        permissions?: Record<string, string>;
    } | null;
    token: string | null;
    login: (token?: string, refreshToken?: string) => Promise<void>;
    logout: () => void;
    refresh: () => Promise<void>;
    isAuthenticated: boolean;
    loading: boolean;
    hasModuleAccess: (module: string, minLevel?: string) => boolean;
    hasPermission: (perm: string) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const router = useRouter();
    const store = useAuthStore();

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
        store.logout();
        window.location.href = '/login';
    }, [store]);

    const fetchUser = useCallback(async (tokenValue?: string) => {
        const activeToken = tokenValue || (typeof window !== 'undefined' ? sessionStorage.getItem('ccf_token') : null);

        if (!activeToken) {
            store.setLoading(false);
            return null;
        }

        const safetyTimer = setTimeout(() => {
            console.warn('[AUTH] fetchUser timeout — forcing loading=false');
            store.setLoading(false);
        }, 6000);

        try {
            const userData = await apiFetch<any>('/auth/me', {
                cache: 'no-store',
                token: activeToken
            });
            if (!userData.permissions) {
                try {
                    const permData = await apiFetch<any>('/auth/me/permissions', {
                        cache: 'no-store',
                        token: activeToken
                    });
                    userData.permissions = permData.permissions;
                } catch {
                    userData.permissions = {};
                }
            }
            store.setAuth(userData, activeToken);
            if (typeof window !== 'undefined' && tokenValue) {
                sessionStorage.setItem('ccf_token', tokenValue);
            }
            return userData;
        } catch (error) {
            console.error('[AUTH] Error fetching user profile:', error);
            const status = (error as any).status;
            if (status === 401) {
                if (typeof window !== 'undefined') {
                    sessionStorage.removeItem('ccf_token');
                    sessionStorage.removeItem('ccf_refresh_token');
                }
                store.setAuth(null, null);
                if (typeof window !== 'undefined') {
                    window.location.href = '/login?expired=1';
                }
            }
            return null;
        } finally {
            clearTimeout(safetyTimer);
            store.setLoading(false);
        }
    }, [store]);

    useEffect(() => {
        fetchUser();
    }, [fetchUser]);

    const login = useCallback(async (accessToken?: string, refreshToken?: string) => {
        store.setLoading(true);
        if (accessToken && typeof window !== 'undefined') {
            sessionStorage.setItem('ccf_token', accessToken);
        }
        if (refreshToken && typeof window !== 'undefined') {
            sessionStorage.setItem('ccf_refresh_token', refreshToken);
        }
        const userData = await fetchUser(accessToken);
        if (userData?.role) {
            redirectByRole(userData.role);
        } else if (accessToken) {
            console.warn("[AUTH] Login success but profile fetch failed. Forcing entry.");
            router.push('/plataforma/admin');
        }
    }, [fetchUser, redirectByRole, router, store]);

    const refresh = useCallback(async () => {
        await fetchUser();
    }, [fetchUser]);

    return (
        <AuthContext.Provider value={{
            user: store.user,
            token: store.token,
            login,
            logout,
            refresh,
            isAuthenticated: store.isAuthenticated,
            loading: store.loading,
            hasModuleAccess: store.hasModuleAccess,
            hasPermission: store.hasPermission,
        }}>
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
