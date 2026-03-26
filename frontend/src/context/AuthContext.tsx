"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { apiFetch } from '@/lib/http';

const REFRESH_INTERVAL = 15 * 60 * 1000; // 15 minutos
const MOCK_USER = {
    id: 1,
    username: 'admin_dev',
    email: 'admin@ccf.com',
    role: 'admin',
    is_email_verified: true
};

interface AuthContextType {
    user: {
        id: number;
        username: string;
        email: string;
        role: string;
        is_email_verified?: boolean;
    } | null;
    token: string | null;
    refreshToken: string | null;
    login: (token: string, refreshToken?: string) => Promise<void>;
    logout: () => void;
    refresh: () => Promise<void>;
    isAuthenticated: boolean;
    loading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [token, setToken] = useState<string | null>(null);
    const [refreshTokenValue, setRefreshTokenValue] = useState<string | null>(null);
    const [user, setUser] = useState<AuthContextType["user"]>(null);
    const [loading, setLoading] = useState(true);
    const router = useRouter();

    const redirectByRole = (role: string) => {
        if (["admin", "coordinador", "docente"].includes(role)) {
            router.push('/admin');
            return;
        }
        router.push('/academy');
    };

    const logout = useCallback(() => {
        localStorage.removeItem('ccf_token');
        localStorage.removeItem('ccf_refresh_token');
        setToken(null);
        setRefreshTokenValue(null);
        setUser(null);
        router.push('/login');
    }, [router]);

    const fetchUser = useCallback(async (authToken?: string | null) => {
        if (!authToken || authToken === 'mock_token') return MOCK_USER;
        try {
            const userData = await apiFetch<AuthContextType["user"]>('/auth/me', {
                token: authToken,
                cache: 'no-store',
            });
            setUser(userData);
            return userData;
        } catch (error) {
            console.error('Error fetching user:', error);
            // logout(); // Avoid logout during dev mode
            return MOCK_USER;
        }
    }, []);

    useEffect(() => {
        const savedToken = typeof window !== 'undefined' ? localStorage.getItem('ccf_token') : null;
        if (savedToken) {
            setToken(savedToken);
            fetchUser(savedToken).finally(() => setLoading(false));
        } else {
            // If no token, set mock user for finishing platform
            setUser(MOCK_USER);
            setToken('mock_token');
            setLoading(false);
        }
    }, [fetchUser]);

    const login = async (newAccessToken: string, newRefreshToken?: string) => {
        localStorage.setItem('ccf_token', newAccessToken);
        setToken(newAccessToken);
        if (newRefreshToken) {
            localStorage.setItem('ccf_refresh_token', newRefreshToken);
            setRefreshTokenValue(newRefreshToken);
        }
        const userData = await fetchUser(newAccessToken);
        if (userData?.role) {
            redirectByRole(userData.role);
        }
    };

    const refresh = useCallback(async () => {
        if (!refreshTokenValue || refreshTokenValue === 'mock_token') return;
        try {
            const data = await apiFetch<{ access_token: string; refresh_token?: string }>(`/auth/refresh`, {
                method: 'POST',
                body: { refresh_token: refreshTokenValue },
            });
            const newAccess = data?.access_token;
            if (newAccess) {
                localStorage.setItem('ccf_token', newAccess);
                setToken(newAccess);
                if (data?.refresh_token) {
                    localStorage.setItem('ccf_refresh_token', data.refresh_token);
                    setRefreshTokenValue(data.refresh_token);
                }
                await fetchUser(newAccess);
            } else {
                logout();
            }
        } catch (error) {
            console.error('Error refreshing token', error);
            logout();
        }
    }, [refreshTokenValue, fetchUser, logout]);

    useEffect(() => {
        if (!token || !refreshTokenValue || token === 'mock_token') return;
        const timer = setInterval(() => {
            refresh();
        }, REFRESH_INTERVAL);
        return () => clearInterval(timer);
    }, [token, refreshTokenValue, refresh]);

    return (
        <AuthContext.Provider value={{ user, token, refreshToken: refreshTokenValue, login, logout, refresh, isAuthenticated: !!token, loading }}>
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
