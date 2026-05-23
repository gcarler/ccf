"use client";

import React, { useEffect, useState, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { Loader2, CheckCircle2, XCircle } from 'lucide-react';
import { apiFetch } from '@/lib/http';

function VerifyEmailContent() {
    const params = useSearchParams();
    const token = params?.get('token');
    const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
    const [message, setMessage] = useState('Confirmando tu correo…');

    useEffect(() => {
        if (!token) {
            setStatus('error');
            setMessage('Token inválido o faltante.');
            return;
        }

        apiFetch('/auth/verify-email', {
            method: 'POST',
            body: { token },
        })
            .then(() => {
                setStatus('success');
                setMessage('¡Tu correo fue verificado correctamente!');
            })
            .catch((err: any) => {
                setStatus('error');
                setMessage(err?.detail?.message || 'No pudimos verificar tu correo.');
            });
    }, [token]);

    const icon = () => {
        if (status === 'loading') return <Loader2 className="w-12 h-8 animate-spin text-primary" />;
        if (status === 'success') return <CheckCircle2 className="w-12 h-8 text-emerald-400" />;
        return <XCircle className="w-12 h-8 text-rose-400" />;
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-slate-950 text-slate-100 px-3">
            <div className="w-full max-w-md bg-slate-900/60 backdrop-blur-xl rounded-lg border border-white/10 shadow-2xl p-4 text-center space-y-6">
                <div className="flex justify-center">{icon()}</div>
                <h1 className="text-lg font-bold">Verificación de correo</h1>
                <p className="text-slate-300 text-sm leading-relaxed">{message}</p>
                <div className="space-y-2">
                    <Link href="/login" className="block w-full py-3 rounded-lg font-semibold uppercase tracking-wide text-sm bg-primary text-white hover:bg-primary/90 transition">
                        Ir al inicio de sesión
                    </Link>
                    <Link href="/auth/forgot" className="block text-sm text-primary font-semibold hover:underline">
                        ¿No te llegó el correo? Solicita otro enlace
                    </Link>
                </div>
            </div>
        </div>
    );
}

export default function VerifyEmailPage() {
    return (
        <Suspense fallback={<div className="min-h-screen flex items-center justify-center bg-slate-950"><Loader2 className="w-8 h-8 animate-spin text-primary" /></div>}>
            <VerifyEmailContent />
        </Suspense>
    );
}

