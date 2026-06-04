"use client";

import { apiFetch } from '@/lib/http';
import { motion } from 'framer-motion';
import { CheckCircle2,Eye,EyeOff,Loader2,XCircle } from 'lucide-react';
import { useRouter,useSearchParams } from 'next/navigation';
import React,{ Suspense,useState } from 'react';

function InitPasswordContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const token = searchParams?.get('token') || '';

    const [password, setPassword] = useState('');
    const [confirm, setConfirm] = useState('');
    const [showPwd, setShowPwd] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');

        if (password.length < 8) {
            setError('La contraseña debe tener al menos 8 caracteres');
            return;
        }
        if (password !== confirm) {
            setError('Las contraseñas no coinciden');
            return;
        }

        setLoading(true);
        try {
            const res = await apiFetch<any>('/v3/auth/initialize-password', {
                method: 'POST',
                body: { token, password, password_confirm: confirm },
            });
            if (res.status === 'success') {
                setSuccess(true);
                setTimeout(() => router.push('/login'), 2500);
            } else {
                setError('Error al configurar la contraseña');
            }
        } catch (err: any) {
            setError(err?.detail || 'Error al configurar la contraseña. El token puede haber expirado.');
        } finally {
            setLoading(false);
        }
    };

    if (success) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-[#0f1116] dark:to-[#1a1b1e]">
                <motion.div
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="bg-[hsl(var(--bg-primary))] dark:bg-[#1e2025] border border-slate-200 dark:border-white/10 rounded-2xl shadow-xl p-8 max-w-md text-center"
                >
                    <CheckCircle2 className="mx-auto mb-4 text-emerald-500" size={48} />
                    <h2 className="text-xl font-bold text-slate-800 dark:text-white mb-2">¡Contraseña Configurada!</h2>
                    <p className="text-slate-500 text-sm">Redirigiendo al inicio de sesión...</p>
                </motion.div>
            </div>
        );
    }

    return (
        <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-[#0f1116] dark:to-[#1a1b1e] p-4">
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-[hsl(var(--bg-primary))] dark:bg-[#1e2025] border border-slate-200 dark:border-white/10 rounded-2xl shadow-xl w-full max-w-md overflow-hidden"
            >
                {/* Header */}
                <div className="bg-gradient-to-r from-blue-600 to-sky-600 px-6 py-5">
                    <h1 className="text-lg font-bold text-white">Configurar Contraseña</h1>
                    <p className="text-blue-100 text-[12px] mt-1">CCF Plataforma</p>
                </div>

                <form onSubmit={handleSubmit} className="p-6 space-y-4">
                    {error && (
                        <div className="flex items-center gap-2 px-3 py-2 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 rounded-lg text-[12px] text-[hsl(var(--destructive))] dark:text-[hsl(var(--destructive))]">
                            <XCircle size={14} />
                            {error}
                        </div>
                    )}

                    <div>
                        <label className="text-[11px] font-semibold uppercase tracking-wide text-slate-500 mb-1.5 block">
                            Nueva Contraseña
                        </label>
                        <div className="relative">
                            <input
                                type={showPwd ? 'text' : 'password'}
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="Mínimo 8 caracteres"
                                className="w-full px-3 py-2.5 text-[13px] bg-[hsl(var(--bg-primary))] dark:bg-[#0f1116] border border-slate-200 dark:border-white/10 rounded-lg text-slate-800 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]/30"
                                required
                                minLength={8}
                            />
                            <button
                                type="button"
                                onClick={() => setShowPwd(!showPwd)}
                                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                            >
                                {showPwd ? <EyeOff size={16} /> : <Eye size={16} />}
                            </button>
                        </div>
                    </div>

                    <div>
                        <label className="text-[11px] font-semibold uppercase tracking-wide text-slate-500 mb-1.5 block">
                            Confirmar Contraseña
                        </label>
                        <input
                            type="password"
                            value={confirm}
                            onChange={(e) => setConfirm(e.target.value)}
                            placeholder="Repite la contraseña"
                            className="w-full px-3 py-2.5 text-[13px] bg-[hsl(var(--bg-primary))] dark:bg-[#0f1116] border border-slate-200 dark:border-white/10 rounded-lg text-slate-800 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]/30"
                            required
                        />
                    </div>

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full py-2.5 bg-gradient-to-r from-blue-600 to-sky-600 hover:from-blue-700 hover:to-sky-700 text-white text-[13px] font-bold rounded-lg transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                    >
                        {loading ? <Loader2 className="animate-spin" size={16} /> : null}
                        {loading ? 'Configurando...' : 'Configurar Contraseña'}
                    </button>
                </form>
            </motion.div>
        </div>
    );
}

export default function InitPasswordPage() {
    return (
        <Suspense fallback={
            <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-[#0f1116] dark:to-[#1a1b1e]">
                <Loader2 className="animate-spin text-[hsl(var(--primary))]" size={32} />
            </div>
        }>
            <InitPasswordContent />
        </Suspense>
    );
}
