"use client";

import React, { useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { UserPlus, Mail, Lock, User, Loader2, ArrowLeft, Eye, EyeOff, ArrowRight, Sparkles, ShieldCheck } from 'lucide-react';
import { apiFetch } from '@/lib/http';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import AuthShowcasePanel from '@/components/AuthShowcasePanel';

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
            <div className="relative min-h-screen w-full flex items-center justify-center overflow-hidden bg-[#020617] p-4 font-sans">
                <div className="absolute inset-0 z-0">
                    <div className="absolute top-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full bg-emerald-600/10 blur-[120px] animate-pulse"></div>
                    <div className="absolute bottom-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-blue-600/10 blur-[120px] animate-pulse delay-700"></div>
                </div>

                <motion.div 
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="relative z-10 w-full max-w-md bg-white/5 backdrop-blur-3xl rounded-[3rem] p-12 border border-white/10 text-center shadow-2xl"
                >
                    <div className="size-20 bg-emerald-500/20 text-emerald-400 rounded-full flex items-center justify-center mx-auto mb-8 shadow-inner">
                        <UserPlus size={40} />
                    </div>
                    <h2 className="text-3xl font-black text-white mb-4 tracking-tight">¡Bienvenido a Casa!</h2>
                    <p className="text-slate-400 mb-10 text-lg leading-relaxed">Tu identidad ministerial ha sido creada. Ya puedes ingresar al ecosistema MESH.</p>
                    <Link href="/login" className="w-full h-14 bg-emerald-600 hover:bg-emerald-500 text-white font-black uppercase tracking-[0.2em] rounded-2xl transition-all shadow-xl shadow-emerald-600/20 flex items-center justify-center gap-3 group">
                        Ir al Acceso <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                    </Link>
                </motion.div>
            </div>
        );
    }

    return (
        <div className="relative min-h-screen w-full flex items-center justify-center overflow-hidden bg-[#020617] p-4 lg:p-8 font-sans">
            {/* Immersive Background */}
            <div className="absolute inset-0 z-0">
                <div className="absolute top-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full bg-indigo-600/10 blur-[120px] animate-pulse-soft"></div>
                <div className="absolute bottom-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-blue-600/10 blur-[120px] animate-pulse-soft delay-700"></div>
                <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-[0.03] brightness-100 contrast-150"></div>
            </div>

            <div className="relative z-10 w-full max-w-6xl">
                <Link href="/login" className="absolute top-0 left-0 lg:top-[-40px] flex items-center gap-2 text-slate-500 hover:text-white transition-colors group z-20">
                    <ArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
                    <span className="text-[10px] font-black uppercase tracking-widest">Regresar</span>
                </Link>

                <div className="grid grid-cols-1 lg:grid-cols-[1fr_420px] gap-8 items-center mt-8 lg:mt-0">
                    {/* Left: Showcase */}
                    <div className="hidden lg:block">
                        <motion.div
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ duration: 0.8 }}
                        >
                            <AuthShowcasePanel mode="register" />
                        </motion.div>
                    </div>

                    {/* Right: Register Form */}
                    <motion.div 
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="w-full max-w-[420px] mx-auto bg-white/5 backdrop-blur-2xl rounded-[2.5rem] p-8 md:p-10 border border-white/10 shadow-2xl relative overflow-hidden"
                    >
                        <div className="text-center mb-10">
                            <motion.div className="inline-flex items-center justify-center size-14 rounded-2xl bg-gradient-to-tr from-indigo-600 to-blue-600 shadow-xl shadow-indigo-500/20 mb-6">
                                <UserPlus size={28} className="text-white" />
                            </motion.div>
                            <h1 className="text-3xl font-black text-white tracking-tight mb-2">Nueva Identidad</h1>
                            <p className="text-slate-400 text-sm font-medium">Únete al ecosistema ministerial</p>
                        </div>

                        <form onSubmit={handleSubmit} className="space-y-4">
                            <div className="space-y-2">
                                <label className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] ml-1">Nombre Completo</label>
                                <div className="relative group">
                                    <User className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 w-5 h-5 group-focus-within:text-indigo-400 transition-colors" />
                                    <input
                                        className="w-full h-14 pl-12 pr-4 rounded-2xl bg-white/5 border border-white/10 text-white placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all"
                                        placeholder="Juan Pérez"
                                        type="text"
                                        value={formData.full_name}
                                        onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                                        required
                                    />
                                </div>
                            </div>

                            <div className="space-y-2">
                                <label className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] ml-1">Correo Ministerial</label>
                                <div className="relative group">
                                    <Mail className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 w-5 h-5 group-focus-within:text-indigo-400 transition-colors" />
                                    <input
                                        className="w-full h-14 pl-12 pr-4 rounded-2xl bg-white/5 border border-white/10 text-white placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all"
                                        placeholder="correo@ejemplo.com"
                                        type="email"
                                        value={formData.email}
                                        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                        required
                                    />
                                </div>
                            </div>

                            <div className="space-y-2">
                                <label className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] ml-1">Contraseña</label>
                                <div className="relative group">
                                    <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 w-5 h-5 group-focus-within:text-indigo-400 transition-colors" />
                                    <input
                                        className="w-full h-14 pl-12 pr-12 rounded-2xl bg-white/5 border border-white/10 text-white placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all"
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
                                        {showPassword ? <Eye size={18} /> : <EyeOff size={18} />}
                                    </button>
                                </div>
                            </div>

                            <div className="p-4 rounded-2xl bg-indigo-500/5 border border-white/5">
                                <div className="flex items-center gap-2 mb-1">
                                    <Sparkles size={12} className="text-indigo-400" />
                                    <span className="text-[10px] font-black text-indigo-400 uppercase tracking-widest">Rol: Estudiante</span>
                                </div>
                                <p className="text-[10px] text-slate-500 italic">Acceso estándar a academia y recursos.</p>
                            </div>

                            {error && (
                                <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-2xl text-rose-400 text-xs font-bold text-center">
                                    {error}
                                </div>
                            )}

                            <button
                                type="submit"
                                disabled={loading}
                                className="w-full h-14 mt-4 rounded-2xl bg-indigo-600 hover:bg-indigo-500 text-white font-black text-sm uppercase tracking-[0.2em] shadow-xl shadow-indigo-600/20 flex items-center justify-center gap-3 transition-all active:scale-[0.98] disabled:opacity-50"
                            >
                                {loading ? <Loader2 className="animate-spin" size={20} /> : 'Crear Cuenta Ahora'}
                            </button>
                        </form>

                        <div className="mt-10 text-center">
                            <p className="text-xs text-slate-500 font-medium">
                                ¿Ya eres parte?{' '}
                                <Link href="/login" className="text-indigo-400 font-black uppercase tracking-widest hover:text-indigo-300 transition-colors ml-1">Inicia Sesión</Link>
                            </p>
                        </div>
                    </motion.div>
                </div>
            </div>

            {/* Footer Tag */}
            <div className="absolute bottom-6 left-1/2 -translate-x-1/2 flex items-center gap-2 text-[9px] font-black text-slate-600 uppercase tracking-[0.4em]">
                <ShieldCheck size={12} className="text-indigo-500/50" /> Identity Protected · MESH Auth v2.0
            </div>
        </div>
    );
}
