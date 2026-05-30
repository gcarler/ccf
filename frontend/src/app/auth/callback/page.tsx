"use client";

import { useEffect, useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { Loader2 } from 'lucide-react';

function AuthCallbackContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const { login } = useAuth();
    const [status, setStatus] = useState('Procesando autenticación...');

    useEffect(() => {
        async function handleAuth() {
            // Support both hash params (#token=...) and query params (?token=...)
            // Google SSO redirects with ?token=, v3 login may use #token=
            const hash = typeof window !== 'undefined' ? window.location.hash.slice(1) : '';
            const hashParams = new URLSearchParams(hash);

            const token = hashParams.get('token') || searchParams?.get('token') || searchParams?.get('access_token');
            const refresh = hashParams.get('refresh') || searchParams?.get('refresh') || searchParams?.get('refresh_token');

            if (!token) {
                setStatus('Error: No se recibió token de autenticación');
                setTimeout(() => router.push('/login'), 3000);
                return;
            }

            setStatus('Autenticación exitosa. Redirigiendo...');
            
            // Clean URL params after extracting token
            if (typeof window !== 'undefined') {
                window.history.replaceState({}, document.title, '/auth/callback');
            }

            await login(token, refresh ?? undefined);
            router.push('/plataforma/dashboard');
        }
        
        handleAuth();
    }, []); // Run once on mount; avoid dependency on mutable objects

    return (
        <div className="flex min-h-screen items-center justify-center bg-gray-50">
            <div className="text-center">
                <Loader2 className="animate-spin mx-auto mb-4 text-ccf-blue-dark" size={32} />
                <p className="text-gray-600 font-medium">{status}</p>
            </div>
        </div>
    );
}

    return (
        <div className="flex min-h-screen items-center justify-center bg-gray-50">
            <div className="text-center">
                <Loader2 className="animate-spin mx-auto mb-4 text-ccf-blue-dark" size={32} />
                <p className="text-gray-600 font-medium">{status}</p>
            </div>
        </div>
    );
}

export default function AuthCallbackPage() {
    return (
        <Suspense fallback={
            <div className="flex min-h-screen items-center justify-center bg-gray-50">
                <Loader2 className="animate-spin mx-auto mb-4 text-ccf-blue-dark" size={32} />
            </div>
        }>
            <AuthCallbackContent />
        </Suspense>
    );
}
