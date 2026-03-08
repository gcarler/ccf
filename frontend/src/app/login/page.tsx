"use client";

import React, { useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { Lock, Mail, Loader2, ArrowLeft, EyeOff, Eye } from 'lucide-react';
import { apiUrl } from '@/lib/api';
import Link from 'next/link';

// Church icon approximation using Lucide or a generic building
const ChurchIcon = ({ className }: { className?: string }) => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
        <path d="M12 2 v6"></path>
        <path d="M9 5 h6"></path>
        <path d="M12 8 L4 14 v8 h16 v-8 Z"></path>
        <path d="M12 22 v-6"></path>
        <path d="M10 22 v-4 h4 v4"></path>
    </svg>
);

export default function LoginPage() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const { login } = useAuth();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError('');

        try {
            const formData = new FormData();
            formData.append('username', email);
            formData.append('password', password);

            const response = await fetch(apiUrl('/auth/login'), {
                method: 'POST',
                body: formData,
            });

            if (response.ok) {
                const data = await response.json();
                await login(data.access_token);
            } else {
                const errData = await response.json();
                setError(errData.detail || 'Error al iniciar sesión');
            }
        } catch (err) {
            setError('Error de conexión con el servidor');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="relative flex min-h-screen w-full flex-col overflow-x-hidden bg-gradient-to-b from-primary/10 to-slate-50 dark:from-primary/20 dark:to-slate-950">
            {/* Header / App Bar */}
            <div className="flex items-center p-4 pb-2 justify-between z-10">
                <Link href="/" className="text-slate-900 dark:text-slate-100 flex size-12 shrink-0 items-center justify-start hover:bg-slate-200 dark:hover:bg-slate-800 rounded-full transition-colors">
                    <ArrowLeft className="w-6 h-6" />
                </Link>
                <h2 className="text-slate-900 dark:text-slate-100 text-lg font-bold leading-tight tracking-tight flex-1 text-center pr-12">Acceso al Ministerio</h2>
            </div>

            <div className="flex flex-col flex-1 px-6 pb-8 z-10 max-w-md mx-auto w-full">
                {/* Logo Section with subtle glowing effect */}
                <div className="flex flex-col items-center justify-center pt-8 pb-10">
                    <div className="relative">
                        <div className="absolute inset-0 bg-primary/30 blur-2xl rounded-full"></div>
                        <div className="relative bg-white dark:bg-slate-800 p-6 rounded-full shadow-xl">
                            <ChurchIcon className="text-primary w-12 h-12" />
                        </div>
                    </div>
                    <h1 className="text-slate-900 dark:text-slate-100 text-3xl font-bold mt-8 text-center animate-in fade-in slide-in-from-bottom-4 duration-500">¡Bienvenido!</h1>
                    <p className="text-slate-600 dark:text-slate-400 text-base font-normal mt-2 text-center animate-in fade-in slide-in-from-bottom-4 duration-700 delay-100">Inicia sesión para continuar tu formación espiritual</p>
                </div>

                {/* Login Form */}
                <form onSubmit={handleSubmit} className="flex flex-col gap-4 animate-in fade-in slide-in-from-bottom-6 duration-700 delay-200">
                    <div className="flex flex-col gap-2">
                        <label className="text-slate-700 dark:text-slate-300 text-sm font-semibold ml-1">Correo electrónico</label>
                        <div className="relative">
                            <Mail className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 w-5 h-5" />
                            <input
                                className="w-full h-14 pl-12 pr-4 rounded-xl border-0 bg-white/70 dark:bg-slate-800/70 backdrop-blur-md text-slate-900 dark:text-slate-100 ring-1 ring-primary/10 focus:ring-2 focus:ring-primary placeholder:text-slate-400 transition-all"
                                placeholder="ejemplo@iglesia.com"
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                required
                            />
                        </div>
                    </div>

                    <div className="flex flex-col gap-2">
                        <label className="text-slate-700 dark:text-slate-300 text-sm font-semibold ml-1">Contraseña</label>
                        <div className="relative">
                            <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 w-5 h-5" />
                            <input
                                className="w-full h-14 pl-12 pr-12 rounded-xl border-0 bg-white/70 dark:bg-slate-800/70 backdrop-blur-md text-slate-900 dark:text-slate-100 ring-1 ring-primary/10 focus:ring-2 focus:ring-primary placeholder:text-slate-400 transition-all"
                                placeholder="••••••••"
                                type={showPassword ? "text" : "password"}
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                required
                            />
                            <button
                                type="button"
                                onClick={() => setShowPassword(!showPassword)}
                                className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 cursor-pointer hover:text-slate-600 dark:hover:text-slate-200 transition-colors"
                            >
                                {showPassword ? <Eye className="w-5 h-5" /> : <EyeOff className="w-5 h-5" />}
                            </button>
                        </div>
                    </div>

                    <div className="flex justify-end mt-1">
                        <a className="text-primary text-sm font-medium hover:underline transition-all" href="#">¿Olvidaste tu contraseña?</a>
                    </div>

                    {error && (
                        <div className="bg-rose-500/10 border border-rose-500/20 text-rose-500 p-4 rounded-xl text-sm animate-in fade-in">
                            {error}
                        </div>
                    )}

                    {/* Action Buttons */}
                    <div className="flex flex-col gap-4 mt-6">
                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full h-14 flex items-center justify-center gap-2 bg-primary text-white font-bold rounded-xl shadow-lg shadow-primary/30 active:scale-95 transition-transform disabled:opacity-70 disabled:active:scale-100"
                        >
                            {loading ? <Loader2 className="animate-spin w-5 h-5" /> : null}
                            {loading ? 'Iniciando Sesión...' : 'Iniciar Sesión'}
                        </button>

                        <div className="flex items-center gap-4 my-2">
                            <div className="h-px flex-1 bg-slate-300 dark:bg-slate-700"></div>
                            <span className="text-slate-500 text-xs font-bold uppercase tracking-wider">o</span>
                            <div className="h-px flex-1 bg-slate-300 dark:bg-slate-700"></div>
                        </div>

                        <Link href="/register" className="flex items-center justify-center w-full h-14 bg-primary/10 dark:bg-primary/20 text-primary font-bold rounded-xl active:scale-95 transition-transform border border-primary/20 hover:bg-primary/20 dark:hover:bg-primary/30">
                            Registrarse
                        </Link>
                    </div>
                </form>

                {/* Social/Guest Footer */}
                <div className="mt-auto pt-8 text-center animate-in fade-in duration-1000 delay-300">
                    <p className="text-slate-500 dark:text-slate-400 text-sm">
                        ¿Primera vez aquí? <Link href="/" className="text-primary font-bold hover:underline transition-all">Explora como invitado</Link>
                    </p>
                </div>
            </div>

            {/* Abstract Decorative Element */}
            <div className="absolute -bottom-20 -left-20 size-64 bg-primary/10 rounded-full blur-3xl pointer-events-none"></div>
            <div className="absolute -top-20 -right-20 size-64 bg-primary/5 rounded-full blur-3xl pointer-events-none"></div>
        </div>
    );
}
