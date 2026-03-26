"use client";

import React, { useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { UserPlus, Mail, Lock, User, Loader2, ArrowLeft, Eye, EyeOff, ArrowRight } from 'lucide-react';
import { apiUrl } from '@/lib/api';
import { apiFetch } from '@/lib/http';
import Link from 'next/link';
import AuthShowcasePanel from '@/components/AuthShowcasePanel';

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
            await apiFetch('/auth/register', {
                method: 'POST',
                body: {
                    username: formData.email,
                    email: formData.email,
                    password: formData.password,
                    full_name: formData.full_name,
                    role: formData.role
                },
            });

            setSuccess(true);
        } catch (err: any) {
            const detail = err?.detail?.detail || err?.detail?.message;
            setError(detail || 'Error de conexión con el servidor');
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
                        <p className="text-slate-300 mb-8 font-normal text-lg">Revisa tu correo para confirmar tu cuenta antes de iniciar sesión.</p>
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
        <div className="relative flex min-h-screen w-full items-center justify-center overflow-hidden bg-[#020617] font-display">
            {/* Immersive Kinetic Background */}
            <div className="absolute inset-0 z-0">
                <div className="absolute top-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full bg-indigo-600/20 blur-[120px] animate-pulse-soft"></div>
                <div className="absolute bottom-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-blue-600/20 blur-[120px] animate-pulse-soft delay-700"></div>
                <div className="absolute top-[20%] left-[10%] w-[30%] h-[30%] rounded-full bg-purple-600/10 blur-[100px] animate-pulse-soft delay-1000"></div>
                
                {/* Animated Grid Overlay */}
                <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 brightness-100 contrast-150"></div>
            </div>

            <div className="relative z-10 w-full max-w-6xl px-6 py-12">
                <Link href="/login" className="absolute top-6 left-6 flex items-center gap-2 text-slate-400 hover:text-white transition-colors group">
                    <div className="p-2 rounded-full bg-white/5 border border-white/10 group-hover:bg-white/10 transition-all">
                        <ArrowLeft className="w-4 h-4" />
                    </div>
                    <span className="text-xs font-bold uppercase tracking-widest">Regresar al Acceso</span>
                </Link>

                <div className="flex flex-col gap-10 lg:grid lg:grid-cols-[minmax(0,460px)_minmax(0,1fr)] lg:items-center">
                    {/* Deep Glass Register Card */}
                    <div className="order-2 w-full max-w-[520px] mx-auto lg:order-1 glass-card p-10 rounded-[2.5rem] border border-white/10 shadow-2xl animate-fade-in-up">
                        <div className="flex flex-col items-center mb-8">
                            <div className="relative mb-6">
                                 <div className="absolute inset-0 bg-indigo-500/40 blur-2xl rounded-full animate-pulse"></div>
                                 <div className="relative bg-slate-900 border border-white/10 p-5 rounded-[2rem] shadow-2xl">
                                    <UserPlus className="text-indigo-400 w-10 h-10" />
                                 </div>
                            </div>
                            <h1 className="text-3xl font-black text-white tracking-tighter mb-2">Nueva Cuenta</h1>
                            <p className="text-slate-400 text-sm font-medium text-center">Únete al ecosistema de formación espiritual más avanzado</p>
                        </div>

                        <form onSubmit={handleSubmit} className="space-y-4">
                        <div className="space-y-2">
                            <label className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] ml-1">Nombre y Apellido</label>
                            <div className="group relative">
                                <User className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 w-5 h-5 group-focus-within:text-indigo-400 transition-colors" />
                                <input
                                    className="w-full h-14 pl-12 pr-4 rounded-2xl bg-white/5 border border-white/10 text-white placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/50 transition-all"
                                    placeholder="Juan Pérez"
                                    type="text"
                                    value={formData.full_name}
                                    onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                                    required
                                />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <label className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] ml-1">Correo Electrónico</label>
                            <div className="group relative">
                                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 w-5 h-5 group-focus-within:text-indigo-400 transition-colors" />
                                <input
                                    className="w-full h-14 pl-12 pr-4 rounded-2xl bg-white/5 border border-white/10 text-white placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/50 transition-all"
                                    placeholder="correo@ejemplo.com"
                                    type="email"
                                    value={formData.email}
                                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                    required
                                />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <label className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] ml-1">Contraseña Maestra</label>
                            <div className="group relative">
                                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 w-5 h-5 group-focus-within:text-indigo-400 transition-colors" />
                                <input
                                    className="w-full h-14 pl-12 pr-12 rounded-2xl bg-white/5 border border-white/10 text-white placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/50 transition-all"
                                    placeholder="••••••••"
                                    type={showPassword ? "text" : "password"}
                                    value={formData.password}
                                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                                    required
                                    minLength={6}
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white transition-colors"
                                >
                                    {showPassword ? <Eye className="w-5 h-5" /> : <EyeOff className="w-5 h-5" />}
                                </button>
                            </div>
                        </div>

                        <div className="p-4 rounded-2xl bg-indigo-500/5 border border-white/5 space-y-1">
                            <p className="text-[10px] font-black text-indigo-400 uppercase tracking-widest">Tipo de Membresía</p>
                            <p className="text-xs text-slate-400 font-medium">Estudiante / Miembro Estándar</p>
                            <p className="text-[9px] text-slate-600 italic">Los roles avanzados requieren verificación manual.</p>
                        </div>

                        {error && (
                            <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs font-bold animate-pulse text-center">
                                {error}
                            </div>
                        )}

                        <button
                            type="submit"
                            disabled={loading}
                            className="relative w-full h-14 mt-6 overflow-hidden rounded-2xl bg-indigo-600 font-black text-white uppercase tracking-widest shadow-xl shadow-indigo-600/20 hover:bg-indigo-500 active:scale-[0.98] transition-all disabled:opacity-50 group"
                        >
                            <div className="relative z-10 flex items-center justify-center gap-2">
                                {loading ? <Loader2 className="animate-spin w-5 h-5" /> : null}
                                {loading ? 'Creando identidad...' : 'Crear Cuenta'}
                            </div>
                            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:animate-shimmer transition-transform"></div>
                        </button>
                        </form>

                        <p className="mt-8 text-center text-xs font-medium text-slate-500">
                            ¿Ya eres parte?{' '}
                            <Link href="/login" className="text-indigo-400 font-black uppercase tracking-widest hover:text-indigo-300 transition-colors ml-1">
                                Inicia Sesión
                            </Link>
                        </p>
                    </div>

                    <AuthShowcasePanel mode="register" className="order-1 lg:order-2" />
                </div>

                <div className="mt-8 text-center">
                    <p className="text-[9px] font-black text-slate-600 uppercase tracking-[0.4em]">Integrated Intelligence Ecosystem v2.0</p>
                </div>
            </div>
        </div>
    );
}
