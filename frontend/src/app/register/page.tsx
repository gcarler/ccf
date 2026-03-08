"use client";

import React, { useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { UserPlus, Mail, Lock, User, Loader2, ArrowLeft, Eye, EyeOff, ArrowRight } from 'lucide-react';
import { apiUrl } from '@/lib/api';
import Link from 'next/link';

// Church icon approximation
const ChurchIcon = ({ className }: { className?: string }) => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
        <path d="M12 2 v6"></path>
        <path d="M9 5 h6"></path>
        <path d="M12 8 L4 14 v8 h16 v-8 Z"></path>
        <path d="M12 22 v-6"></path>
        <path d="M10 22 v-4 h4 v4"></path>
    </svg>
);

export default function RegisterPage() {
    const [formData, setFormData] = useState({
        full_name: '',
        email: '',
        password: '',
        role: 'estudiante'
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState(false);
    const [showPassword, setShowPassword] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError('');

        try {
            const response = await fetch(apiUrl('/auth/register'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    username: formData.email,
                    email: formData.email,
                    password: formData.password,
                    full_name: formData.full_name,
                    role: formData.role
                }),
            });

            if (response.ok) {
                setSuccess(true);
            } else {
                const errData = await response.json();
                setError(errData.detail || 'Error al registrar usuario');
            }
        } catch (err) {
            setError('Error de conexión con el servidor');
        } finally {
            setLoading(false);
        }
    };

    if (success) {
        return (
            <div className="relative flex h-screen w-full flex-col overflow-hidden bg-slate-950 font-display">
                <div className="absolute inset-0 z-0">
                    <div className="absolute inset-0 bg-gradient-to-b from-slate-950/40 via-slate-950/60 to-slate-950 z-10"></div>
                    <div className="absolute inset-0 bg-primary/20 z-10"></div>
                </div>

                <div className="relative z-20 flex flex-1 flex-col justify-center px-6">
                    <div className="glass-card rounded-2xl p-10 text-center animate-in zoom-in duration-500 max-w-md mx-auto w-full bg-slate-900/60 backdrop-blur-xl border border-white/10">
                        <div className="w-20 h-20 bg-primary/20 text-primary rounded-full flex items-center justify-center mx-auto mb-6">
                            <UserPlus size={40} />
                        </div>
                        <h2 className="text-3xl font-bold text-slate-100 mb-4 tracking-tight">¡Bienvenido a Casa!</h2>
                        <p className="text-slate-300 mb-8 font-normal text-lg">Tu cuenta ha sido creada. Ya puedes iniciar sesión y continuar tu formación espiritual.</p>
                        <Link href="/login" className="w-full bg-primary hover:bg-primary/90 text-white font-bold py-4 rounded-xl transition-all shadow-lg shadow-primary/25 active:scale-[0.98] flex items-center justify-center gap-2">
                            Ir al Acceso
                            <ArrowRight className="w-5 h-5" />
                        </Link>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="relative flex min-h-screen w-full flex-col overflow-x-hidden bg-slate-950 font-display text-slate-100">
            {/* Background Image with Overlay */}
            <div className="fixed inset-0 z-0">
                <div className="absolute inset-0 bg-gradient-to-b from-slate-950/80 via-slate-950/90 to-slate-950 z-10"></div>
                <div className="absolute inset-0 bg-primary/10 z-10"></div>
                {/* Fallback pattern if image is missing */}
                <div className="absolute inset-0 z-0 opacity-20" style={{ backgroundImage: 'radial-gradient(circle at 2px 2px, white 1px, transparent 0)', backgroundSize: '40px 40px' }}></div>
            </div>

            {/* Header */}
            <div className="relative z-20 flex items-center justify-between p-6">
                <div className="flex items-center gap-3">
                    <div className="bg-primary/20 p-2.5 rounded-xl border border-primary/20">
                        <ChurchIcon className="text-primary w-6 h-6" />
                    </div>
                    <span className="font-bold tracking-tight text-xl">Ministerio</span>
                </div>
                <Link href="/login" className="flex h-11 w-11 items-center justify-center rounded-full bg-white/5 backdrop-blur-md border border-white/10 hover:bg-white/10 transition-colors">
                    <ArrowLeft className="text-slate-100 w-5 h-5" />
                </Link>
            </div>

            {/* Main Content */}
            <div className="relative z-20 flex flex-1 flex-col justify-center px-6 pb-12 pt-4">
                <div className="mb-8 space-y-2 text-center animate-in fade-in slide-in-from-bottom-4 duration-500">
                    <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-slate-100">Únete a la Familia</h1>
                    <p className="text-slate-300 text-lg">Crea tu cuenta para acceder a la plataforma</p>
                </div>

                {/* Registration Form Card */}
                <div className="glass-card rounded-2xl p-6 md:p-8 max-w-md mx-auto w-full bg-slate-900/40 backdrop-blur-xl border border-white/10 shadow-2xl animate-in fade-in slide-in-from-bottom-8 duration-700 delay-100">
                    <form onSubmit={handleSubmit} className="space-y-5">
                        <div className="flex flex-col gap-2">
                            <label className="text-slate-300 text-sm font-semibold ml-1">Nombre Completo</label>
                            <div className="relative">
                                <User className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 w-5 h-5" />
                                <input
                                    type="text"
                                    value={formData.full_name}
                                    onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                                    className="w-full h-14 pl-12 pr-4 rounded-xl border-0 bg-slate-800/50 backdrop-blur-md text-slate-100 ring-1 ring-white/10 focus:ring-2 focus:ring-primary placeholder:text-slate-500 transition-all font-medium"
                                    placeholder="Juan Pérez"
                                    required
                                />
                            </div>
                        </div>

                        <div className="flex flex-col gap-2">
                            <label className="text-slate-300 text-sm font-semibold ml-1">Correo Electrónico</label>
                            <div className="relative">
                                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 w-5 h-5" />
                                <input
                                    type="email"
                                    value={formData.email}
                                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                    className="w-full h-14 pl-12 pr-4 rounded-xl border-0 bg-slate-800/50 backdrop-blur-md text-slate-100 ring-1 ring-white/10 focus:ring-2 focus:ring-primary placeholder:text-slate-500 transition-all font-medium"
                                    placeholder="tu@correo.com"
                                    required
                                />
                            </div>
                        </div>

                        <div className="flex flex-col gap-2">
                            <label className="text-slate-300 text-sm font-semibold ml-1">Contraseña</label>
                            <div className="relative">
                                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 w-5 h-5" />
                                <input
                                    type="password"
                                    value={formData.password}
                                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                                    className="w-full h-14 pl-12 pr-12 rounded-xl border-0 bg-slate-800/50 backdrop-blur-md text-slate-100 ring-1 ring-white/10 focus:ring-2 focus:ring-primary placeholder:text-slate-500 transition-all font-medium"
                                    placeholder="••••••••"
                                    required
                                    minLength={6}
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 cursor-pointer hover:text-slate-200 transition-colors"
                                >
                                    {showPassword ? <Eye className="w-5 h-5" /> : <EyeOff className="w-5 h-5" />}
                                </button>
                            </div>
                        </div>

                        <div className="flex flex-col gap-2">
                            <label className="text-slate-300 text-sm font-semibold ml-1">Tipo de Cuenta</label>
                            <div className="relative rounded-xl bg-slate-800/30 backdrop-blur-md ring-1 ring-white/5 p-4 text-slate-400 font-medium">
                                Estudiante / Miembro (Acceso estándar)
                            </div>
                            <p className="text-[10px] text-slate-500 mt-1 ml-1 uppercase tracking-wider font-bold">
                                * Roles de docente o líder requieren aprobación administrativa.
                            </p>
                        </div>

                        {error && (
                            <div className="bg-rose-500/20 border border-rose-500/30 text-rose-200 p-4 rounded-xl text-sm font-medium animate-in slide-in-from-top-2">
                                {error}
                            </div>
                        )}

                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full h-14 bg-primary hover:bg-primary/90 text-white font-bold rounded-xl transition-all shadow-lg shadow-primary/25 active:scale-[0.98] flex items-center justify-center gap-2 mt-4 disabled:opacity-70 disabled:active:scale-100"
                        >
                            {loading ? <Loader2 className="animate-spin w-5 h-5" /> : null}
                            {loading ? 'Procesando...' : 'Crear Cuenta'}
                        </button>

                        <p className="text-center text-sm font-normal text-slate-400 pt-4">
                            ¿Ya tienes cuenta?{' '}
                            <Link href="/login" className="text-primary font-bold hover:underline transition-all">
                                Inicia sesión
                            </Link>
                        </p>
                    </form>
                </div>
            </div>
        </div>
    );
}
