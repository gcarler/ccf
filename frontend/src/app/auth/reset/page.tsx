"use client";

import React, { useState, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Loader2, Lock } from 'lucide-react';
import { apiFetch } from '@/lib/http';

function ResetPasswordContent() {
    const params = useSearchParams();
    const router = useRouter();
    const token = params?.get('token');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);

    if (!token) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-slate-950 text-slate-100 px-3">
                <div className="p-4 rounded-lg bg-slate-900 border border-white/10 text-center space-y-4">
                    <h1 className="text-lg font-bold">Token inválido</h1>
                    <p className="text-slate-400 text-sm">El enlace no es válido o ya fue utilizado.</p>
                    <Link href="/auth/forgot" className="text-primary font-semibold text-sm hover:underline">
                        Solicitar uno nuevo
                    </Link>
                </div>
            </div>
        );
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (password !== confirmPassword) {
            setError('Las contraseñas no coinciden');
            return;
        }
        setLoading(true);
        setError(null);
        setMessage(null);
        try {
            await apiFetch('/auth/reset-password', {
                method: 'POST',
                body: { token, password },
            });
            setMessage('Tu contraseña se actualizó correctamente.');
            setTimeout(() => {
                router.push('/login');
            }, 2000);
        } catch (err: any) {
            setError(err?.detail?.message || 'No pudimos actualizar tu contraseña.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-slate-950 text-slate-100 px-3">
            <div className="w-full max-w-md bg-slate-900/60 backdrop-blur-xl rounded-lg border border-white/10 shadow-2xl p-4 space-y-3">
                <div>
                    <h1 className="text-xl font-bold tracking-tight">Restablecer contraseña</h1>
                    <p className="text-slate-400 text-sm mt-2">Crea una nueva contraseña segura para tu cuenta.</p>
                </div>
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div className="space-y-2">
                        <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">Nueva contraseña</label>
                        <div className="relative">
                            <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
                            <input
                                type="password"
                                required
                                minLength={6}
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                className="w-full bg-slate-900 border border-white/10 rounded-lg py-1.5 pl-12 pr-4 text-sm text-white focus:outline-none focus:border-primary"
                                placeholder="••••••••"
                            />
                        </div>
                    </div>
                    <div className="space-y-2">
                        <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">Confirmar contraseña</label>
                        <div className="relative">
                            <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
                            <input
                                type="password"
                                required
                                minLength={6}
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                className="w-full bg-slate-900 border border-white/10 rounded-lg py-1.5 pl-12 pr-4 text-sm text-white focus:outline-none focus:border-primary"
                                placeholder="••••••••"
                            />
                        </div>
                    </div>
                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full py-1.5 bg-primary rounded-lg font-semibold uppercase tracking-wide text-sm hover:bg-primary/90 transition flex items-center justify-center gap-2 disabled:opacity-60"
                    >
                        {loading && <Loader2 className="w-4 h-4 animate-spin" />} Actualizar contraseña
                    </button>
                </form>
                {message && <p className="text-emerald-400 text-sm font-semibold text-center">{message}</p>}
                {error && <p className="text-rose-400 text-sm font-semibold text-center">{error}</p>}
            </div>
        </div>
    );
}

export default function ResetPasswordPage() {
    return (
        <Suspense fallback={<div className="min-h-screen flex items-center justify-center bg-slate-950"><Loader2 className="w-8 h-8 animate-spin text-primary" /></div>}>
            <ResetPasswordContent />
        </Suspense>
    );
}

