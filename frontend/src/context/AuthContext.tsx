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
    const [token, setToken] = useState<string | null>(null);
    const [user, setUser] = useState<AuthContextType["user"]>(null);
    const [loading, setLoading] = useState(true);
    const router = useRouter();

    const redirectByRole = useCallback((role: string) => {
        if (["admin", "coordinador", "docente"].includes(role)) {
            router.push('/admin');
            return;
        }
        router.push('/academy');
    }, [router]);

    const logout = useCallback(() => {
        void apiFetch('/auth/logout', { method: 'POST' }).catch(() => {});
        setToken(null);
        setUser(null);
        router.push('/login');
    }, [router]);

    const fetchUser = useCallback(async () => {
        try {
            const userData = await apiFetch<AuthContextType["user"]>('/auth/me', {
                cache: 'no-store',
            });
            setUser(userData);
            setToken('cookie');
            return userData;
        } catch (error) {
            console.error('Error fetching user:', error);
            setUser(null);
            setToken(null);
            return null;
        }
    }, []);

    useEffect(() => {
        fetchUser().finally(() => setLoading(false));
    }, [fetchUser]);

    const login = useCallback(async () => {
        const userData = await fetchUser();
        if (userData?.role) {
            redirectByRole(userData.role);
        }
    }, [fetchUser, redirectByRole]);

    const refresh = useCallback(async () => {
        await fetchUser();
    }, [fetchUser]);

    return (
        <AuthContext.Provider value={{ user, token, login, logout, refresh, isAuthenticated: !!user, loading }}>
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
