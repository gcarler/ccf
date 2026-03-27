"use client";

import React, { useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { Lock, Mail, Loader2, ArrowLeft, EyeOff, Eye, Sparkles, ShieldCheck, Zap } from 'lucide-react';
import { apiFetch } from '@/lib/http';
import Link from 'next/link';
import AuthShowcasePanel from '@/components/AuthShowcasePanel';
import { motion } from 'framer-motion';
import clsx from 'clsx';

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
            const formData = new URLSearchParams();
            formData.append('username', email);
            formData.append('password', password);

            await apiFetch('/auth/login', {
                method: 'POST',
                body: formData,
            });
            await login();
        } catch (err: any) {
            const detail = err?.detail?.detail || err?.detail?.message;
            setError(detail || 'Error al iniciar sesión. Verifica tus credenciales.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="relative min-h-screen w-full flex items-center justify-center overflow-hidden bg-[#07090d] selection:bg-blue-500/30">
            {/* 1. Kinetic Background (Clean Productivity Standard) */}
            <div className="absolute inset-0 z-0">
                <div className="absolute top-[-10%] left-[-10%] w-[60%] h-[60%] rounded-full bg-blue-600/10 blur-[140px] animate-pulse"></div>
                <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] rounded-full bg-indigo-600/10 blur-[140px] animate-pulse delay-1000"></div>
                
                {/* Noise Texture */}
                <div className="absolute inset-0 opacity-[0.03] pointer-events-none bg-[url('https://grainy-gradients.vercel.app/noise.svg')]"></div>
                
                {/* Subtle Grid */}
                <div className="absolute inset-0 bg-[linear-gradient(to_right,#8080800a_1px,transparent_1px),linear-gradient(to_bottom,#8080800a_1px,transparent_1px)] bg-[size:4rem_4rem]"></div>
            </div>

            <div className="relative z-10 w-full max-w-[1400px] px-6 py-12">
                <div className="flex flex-col lg:grid lg:grid-cols-12 gap-16 items-center">
                    
                    {/* 2. Login Card (Level 2 Elevation) */}
                    <motion.div 
                        initial={{ opacity: 0, x: -40 }}
                        animate={{ opacity: 1, x: 0 }}
                        className="lg:col-span-5 w-full max-w-[480px] mx-auto"
                    >
                        <div className="bg-white/5 backdrop-blur-2xl p-10 lg:p-14 rounded-[3.5rem] border border-white/10 shadow-[var(--shadow-floating)] relative overflow-hidden">
                            {/* Decorative Top Glow */}
                            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-1/2 h-[1px] bg-gradient-to-r from-transparent via-blue-500 to-transparent" />

                            <header className="mb-12 space-y-4">
                                <Link href="/" className="inline-flex items-center gap-2 text-slate-500 hover:text-white transition-all group mb-4">
                                    <ArrowLeft size={16} className="group-hover:-translate-x-1 transition-transform" />
                                    <span className="text-[10px] font-black uppercase tracking-[0.3em]">Inicio</span>
                                </Link>
                                <div className="space-y-2">
                                    <div className="inline-flex items-center gap-2 px-3 py-1 bg-blue-500/10 border border-blue-500/20 rounded-lg text-[9px] font-black text-blue-400 uppercase tracking-widest">
                                        <ShieldCheck size={12} /> Acceso Seguro
                                    </div>
                                    <h1 className="text-4xl font-black text-white tracking-tighter leading-none">
                                        Bienvenido <span className="text-blue-500">de nuevo.</span>
                                    </h1>
                                    <p className="text-slate-400 font-medium leading-relaxed">Gestiona tu propósito y comunidad en un solo lugar.</p>
                                </div>
                            </header>

                            <form onSubmit={handleSubmit} className="space-y-6">
                                <div className="space-y-2">
                                    <label className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] ml-2">Identidad Digital</label>
                                    <div className="relative group">
                                        <Mail className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-blue-500 transition-colors" size={18} />
                                        <input 
                                            type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
                                            placeholder="correo@ejemplo.com"
                                            className="w-full h-16 pl-14 pr-6 bg-white/5 border border-white/10 rounded-2xl text-white font-bold placeholder:text-slate-600 focus:outline-none focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500/50 transition-all"
                                        />
                                    </div>
                                </div>

                                <div className="space-y-2">
                                    <div className="flex justify-between items-center px-2">
                                        <label className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em]">Llave de Acceso</label>
                                        <Link href="/auth/forgot" className="text-[10px] font-black text-blue-500 hover:underline uppercase tracking-widest">¿Olvidaste?</Link>
                                    </div>
                                    <div className="relative group">
                                        <Lock className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-blue-500 transition-colors" size={18} />
                                        <input 
                                            type={showPassword ? "text" : "password"} required value={password} onChange={(e) => setPassword(e.target.value)}
                                            placeholder="••••••••"
                                            className="w-full h-16 pl-14 pr-14 bg-white/5 border border-white/10 rounded-2xl text-white font-bold placeholder:text-slate-600 focus:outline-none focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500/50 transition-all"
                                        />
                                        <button 
                                            type="button" onClick={() => setShowPassword(!showPassword)}
                                            className="absolute right-5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white transition-colors"
                                        >
                                            {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                                        </button>
                                    </div>
                                </div>

                                {error && (
                                    <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-2xl text-rose-400 text-xs font-bold text-center">
                                        {error}
                                    </motion.div>
                                )}

                                <button 
                                    type="submit" disabled={loading}
                                    className="w-full h-16 bg-blue-600 hover:bg-blue-500 text-white rounded-2xl font-black uppercase tracking-[0.2em] text-xs shadow-2xl shadow-blue-600/20 active:scale-[0.98] transition-all disabled:opacity-50 group relative overflow-hidden"
                                >
                                    <span className="relative z-10 flex items-center justify-center gap-3">
                                        {loading ? <Loader2 className="animate-spin" size={20} /> : <><Zap size={18} fill="currentColor" /> Iniciar Sesión</>}
                                    </span>
                                    <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:animate-shimmer transition-transform" />
                                </button>
                            </form>

                            <footer className="mt-12 pt-10 border-t border-white/5 flex flex-col items-center gap-6">
                                <p className="text-slate-500 text-xs font-medium">¿Aún no tienes cuenta?</p>
                                <Link href="/register" className="w-full py-4 rounded-2xl border border-white/10 text-white font-black text-[10px] uppercase tracking-widest text-center hover:bg-white/5 transition-all active:scale-95">
                                    Crear Nueva Identidad
                                </Link>
                                <p className="text-[9px] font-black text-slate-600 uppercase tracking-[0.4em] mt-4">Unified Access Protocol v3.0</p>
                            </footer>
                        </div>
                    </motion.div>

                    {/* 3. Showcase Panel (Optimism Standard) */}
                    <div className="lg:col-span-7 hidden lg:block">
                        <AuthShowcasePanel mode="login" />
                    </div>
                </div>
            </div>
        </div>
    );
}
