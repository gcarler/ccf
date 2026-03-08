"use client";

import React, { createContext, useContext, useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { apiUrl } from '@/lib/api';

interface AuthContextType {
    user: {
        id: number;
        username: string;
        email: string;
        role: string;
    } | null;
    token: string | null;
    login: (token: string) => Promise<void>;
    logout: () => void;
    isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [token, setToken] = useState<string | null>(null);
    const [user, setUser] = useState<AuthContextType["user"]>(null);
    const router = useRouter();

    const redirectByRole = (role: string) => {
        if (["admin", "coordinador", "docente"].includes(role)) {
            router.push('/admin');
            return;
        }
        router.push('/academy');
    };

    useEffect(() => {
        const savedToken = localStorage.getItem('ccf_token');
        if (savedToken) {
            setToken(savedToken);
            fetchUser(savedToken);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const fetchUser = async (authToken: string) => {
        try {
            const response = await fetch(apiUrl('/auth/me'), {
                headers: { 'Authorization': `Bearer ${authToken}` }
            });
            if (response.ok) {
                const userData = await response.json();
                setUser(userData);
                return userData;
            } else {
                logout();
                return null;
            }
        } catch (error) {
            console.error("Error fetching user:", error);
            logout();
            return null;
        }
    };

    const login = async (newToken: string) => {
        localStorage.setItem('ccf_token', newToken);
        setToken(newToken);
        const userData = await fetchUser(newToken);
        if (userData?.role) {
            redirectByRole(userData.role);
        }
    };

    const logout = () => {
        localStorage.removeItem('ccf_token');
        setToken(null);
        setUser(null);
        router.push('/login');
    };

    return (
        <AuthContext.Provider value={{ user, token, login, logout, isAuthenticated: !!token }}>
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
