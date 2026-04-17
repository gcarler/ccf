"use client";

import React, { useState } from 'react';
import Link from 'next/link';
import { Loader2, Mail, ArrowLeft } from 'lucide-react';
import { apiFetch } from '@/lib/http';
import AuthShowcasePanel from '@/components/AuthShowcasePanel';

export default function ForgotPasswordPage() {
    const [email, setEmail] = useState('');
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setMessage(null);
        setError(null);
        try {
            await apiFetch('/auth/forgot-password', {
                method: 'POST',
                body: { email },
            });
            setMessage('Te enviamos un correo con instrucciones para restablecer tu contraseña.');
        } catch (err: any) {
            setError(err?.detail?.message || 'No pudimos procesar tu solicitud.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="relative min-h-screen w-full overflow-hidden bg-[#020617] text-white">
            <div className="absolute inset-0 z-0">
                <div className="absolute top-[-15%] left-[-15%] w-[45%] h-[45%] rounded-full bg-indigo-600/30 blur-[130px] animate-pulse-soft"></div>
                <div className="absolute bottom-[-20%] right-[-10%] w-[55%] h-[55%] rounded-full bg-blue-500/20 blur-[150px] animate-pulse-soft delay-500"></div>
                <div className="absolute inset-0 bg-[url('/noise.svg')] opacity-[0.18]"></div>
            </div>

            <div className="relative z-10 mx-auto flex w-full max-w-6xl flex-col gap-10 px-6 py-12 lg:grid lg:grid-cols-[minmax(0,420px)_minmax(0,1fr)] lg:items-center">
                <Link href="/login" className="absolute top-6 left-6 flex items-center gap-2 text-slate-400 hover:text-white transition-colors group">
                    <div className="p-2 rounded-full bg-white/5 border border-white/10 group-hover:bg-white/10 transition-all">
                        <ArrowLeft className="w-4 h-4" />
                    </div>
                    <span className="text-xs font-bold uppercase tracking-widest">Volver al acceso</span>
                </Link>

                <div className="order-2 w-full max-w-[480px] mx-auto lg:order-1 glass-card rounded-[2.2rem] border border-white/10 p-10 shadow-2xl">
                    <div className="mb-8 space-y-3 text-center">
                        <p className="text-[11px] font-black uppercase tracking-[0.35em] text-slate-500">Recuperar acceso</p>
                        <h1 className="text-3xl font-black tracking-tight text-white">¿Olvidaste tu contraseña?</h1>
                        <p className="text-slate-400 text-sm">Ingresa tu correo y te enviaremos un enlace seguro para restablecerla.</p>
                    </div>
                    <form onSubmit={handleSubmit} className="space-y-5">
                        <div className="space-y-2">
                            <label className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-500">Correo electrónico</label>
                            <div className="relative">
                                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
                                <input
                                    type="email"
                                    required
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    className="w-full bg-white/5 border border-white/10 rounded-2xl py-4 pl-12 pr-4 text-sm text-white focus:outline-none focus:ring-2 focus:ring-primary/40"
                                    placeholder="tu@correo.com"
                                />
                            </div>
                        </div>
                        <button
                            type="submit"
                            disabled={loading}
                            className="relative w-full overflow-hidden rounded-2xl bg-primary py-4 text-sm font-black uppercase tracking-[0.25em] shadow-lg shadow-primary/30 transition hover:bg-primary/90 disabled:opacity-60 flex items-center justify-center gap-2"
                        >
                            {loading && <Loader2 className="w-4 h-4 animate-spin" />} Enviar enlace seguro
                        </button>
                    </form>
                    {message && <p className="mt-6 text-center text-sm font-semibold text-emerald-400">{message}</p>}
                    {error && <p className="mt-6 text-center text-sm font-semibold text-rose-400">{error}</p>}
                    <div className="mt-8 text-center text-xs text-slate-400">
                        ¿Recordaste tu clave?{' '}
                        <Link href="/login" className="font-bold text-primary hover:text-primary/80">
                            Inicia sesión
                        </Link>
                    </div>
                </div>

                <AuthShowcasePanel mode="login" className="order-1 lg:order-2" />
            </div>
        </div>
    );
}

