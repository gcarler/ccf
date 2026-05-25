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
        if (!searchParams) {
            setStatus('Error: No hay parámetros de autenticación');
            setTimeout(() => router.push('/login'), 3000);
            return;
        }
        const token = searchParams.get('token');
        const refresh = searchParams.get('refresh');

        if (!token) {
            setStatus('Error: No se recibió token de autenticación');
            setTimeout(() => router.push('/login'), 3000);
            return;
        }

        login(token, refresh ?? undefined);
        setStatus('Autenticación exitosa. Redirigiendo...');
    }, [searchParams, router, login]);

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
