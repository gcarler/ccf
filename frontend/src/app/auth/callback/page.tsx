"use client";

import { useEffect, useState, Suspense } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { Loader2 } from 'lucide-react';

function AuthCallbackContent() {
    const router = useRouter();
    const { login } = useAuth();
    const [status, setStatus] = useState('Procesando autenticación...');

    useEffect(() => {
        async function handleAuth() {
            // Google OAuth is cookie-based. Never consume access/refresh
            // credentials from query strings or URL fragments. Remove any
            // historical parameters before making the refresh request so they
            // cannot be sent as a Referer to the API.
            if (typeof window !== 'undefined') {
                window.history.replaceState({}, document.title, window.location.pathname);
            }

            let token: string | null = null;
            let refresh: string | null = null;

            setStatus('Validando sesión segura...');
            try {
                const refreshed = await apiFetch<{ access_token?: string; refresh_token?: string }>(
                    '/v3/auth/refresh',
                    { method: 'POST', silent: true },
                );
                token = refreshed.access_token || null;
                refresh = refreshed.refresh_token || null;
            } catch {
                token = null;
            }

            if (!token) {
                setStatus('Error: No se pudo validar la sesión');
                setTimeout(() => router.push('/login'), 3000);
                return;
            }

            setStatus('Autenticación exitosa. Redirigiendo...');
            await login(token, refresh ?? undefined);
            router.push('/plataforma/messages');
        }

        handleAuth();
    }, [login, router]); // login/router are stable

    return (
        <div className="flex min-h-screen items-center justify-center bg-[hsl(var(--bg-muted))]">
            <div className="text-center">
                <Loader2 className="animate-spin mx-auto mb-4 text-ccf-blue-dark" size={32} />
                <p className="text-[hsl(var(--text-primary))] font-medium">{status}</p>
            </div>
        </div>
    );
}

export default function AuthCallbackPage() {
    return (
        <Suspense fallback={
            <div className="flex min-h-screen items-center justify-center bg-[hsl(var(--bg-muted))]">
                <Loader2 className="animate-spin mx-auto mb-4 text-ccf-blue-dark" size={32} />
            </div>
        }>
            <AuthCallbackContent />
        </Suspense>
    );
}
