"use client";

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2, Eye, EyeOff } from 'lucide-react';
import Link from 'next/link';

export default function LoginPage() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const { login, isAuthenticated, user } = useAuth();
    const router = useRouter();

    useEffect(() => {
        if (isAuthenticated && user?.role) {
            const role = user.role.toLowerCase();
            if (["admin", "coordinador", "docente"].includes(role)) {
                router.push('/admin');
            } else {
                router.push('/academy');
            }
        }
    }, [isAuthenticated, user, router]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError('');
        try {
            const formData = new URLSearchParams();
            formData.append('grant_type', 'password');
            formData.append('username', email);
            formData.append('password', password);
            const response = await apiFetch<any>('/auth/login', {
                method: 'POST',
                body: formData,
            });
            if (response.access_token) {
                await login(response.access_token);
            } else {
                setError('No se recibió el token de acceso.');
            }
        } catch (err: any) {
            console.error('[LOGIN ERROR]', err);
            setError('Credenciales incorrectas o problema de conexión.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex w-screen min-h-screen font-sans">
            {/* ── LEFT PANEL: BRANDING ── */}
            <motion.section
                initial={{ opacity: 0, x: -30 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
                className="flex-[1.2] bg-ccf-blue-dark relative flex flex-col justify-between px-[clamp(40px,8%,90px)] py-[clamp(40px,8%,90px)] min-h-screen overflow-hidden"
            >
                {/* Radial glow */}
                <div className="absolute top-[-20%] right-[-20%] w-[140%] h-[140%] pointer-events-none z-0"
                    style={{ background: 'radial-gradient(circle at 70% 30%, rgba(1,138,189,0.25) 0%, transparent 60%)' }}
                />

                {/* Top badge */}
                <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.4 }}
                    className="relative z-10"
                >
                    <div className="inline-flex items-center gap-3 border border-white/20 rounded-full px-5 py-2.5 bg-white/5 backdrop-blur-md">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
                            <path d="M8 22L10 6L12 2L14 6L16 22H8Z" strokeLinejoin="round"/>
                            <circle cx="12" cy="4" r="1.5" fill="white" stroke="none"/>
                        </svg>
                        <span className="text-white font-bold uppercase tracking-[0.2em] text-[10px]">
                            Ministerio Internacional
                        </span>
                    </div>
                </motion.div>

                {/* Title */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.6, duration: 0.8 }}
                    className="relative z-10"
                >
                    <h1 className="font-black tracking-[-0.04em] leading-[0.88] text-white text-[clamp(3rem,6vw,4.5rem)] m-0">
                        EL <br /> FARO
                    </h1>
                    <p className="text-ccf-blue-light text-[clamp(1rem,2vw,1.25rem)] font-black tracking-[0.2em] uppercase mt-6 leading-[1.4]">
                        Comunidad <br /> Cristiana
                    </p>
                    <div className="w-16 h-1.5 bg-white mt-8 rounded-full" />
                </motion.div>

                {/* Bottom motto */}
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 1 }}
                    className="relative z-10"
                >
                    <p className="text-white/90 text-lg font-medium tracking-[0.02em] leading-relaxed">
                        Guiando a las naciones <br /> hacia la luz de la verdad.
                    </p>
                </motion.div>

                {/* Decorative SVG waves */}
                <svg
                    className="absolute bottom-0 left-0 w-full z-0 pointer-events-none"
                    viewBox="0 0 1440 320"
                    preserveAspectRatio="none"
                >
                    <path fill="rgba(255,255,255,0.03)" d="M0,224L48,213.3C96,203,192,181,288,181.3C384,181,480,203,576,218.7C672,235,768,245,864,240C960,235,1056,213,1152,197.3C1248,181,1344,171,1392,165.3L1440,160L1440,320L1392,320C1344,320,1248,320,1152,320C1056,320,960,320,864,320C768,320,672,320,576,320C480,320,384,320,288,320C192,320,96,320,48,320L0,320Z"/>
                    <path fill="rgba(255,255,255,0.06)" d="M0,128L48,144C96,160,192,192,288,197.3C384,203,480,181,576,160C672,139,768,117,864,128C960,139,1056,181,1152,186.7C1248,192,1344,160,1392,144L1440,128L1440,320L1392,320C1344,320,1248,320,1152,320C1056,320,960,320,864,320C768,320,672,320,576,320C480,320,384,320,288,320C192,320,96,320,48,320L0,320Z"/>
                </svg>
            </motion.section>

            {/* ── RIGHT PANEL: FORM ── */}
            <motion.section
                initial={{ opacity: 0, x: 30 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
                className="flex-1 bg-white flex flex-col justify-center px-[clamp(40px,8%,90px)] py-[clamp(40px,8%,90px)] min-h-screen"
            >
                <div className="w-full max-w-[420px] mx-auto">

                    {/* Form header */}
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.3 }}
                        className="mb-14"
                    >
                        <h2 className="text-[clamp(2rem,4vw,2.75rem)] font-extrabold text-ccf-blue-dark tracking-[-0.02em] leading-none m-0 mb-4">
                            Bienvenido
                        </h2>
                        <p className="text-gray-400 font-bold uppercase tracking-[0.2em] text-[10px] m-0">
                            Acceso a la plataforma digital
                        </p>
                    </motion.div>

                    {/* Form */}
                    <form onSubmit={handleSubmit} className="flex flex-col gap-7">

                        {/* Email */}
                        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.45 }}>
                            <label className="text-[10px] font-black text-gray-400 uppercase tracking-[0.15em] block mb-3 ml-2">
                                Email
                            </label>
                            <input
                                type="text"
                                required
                                value={email}
                                onChange={e => setEmail(e.target.value)}
                                placeholder="usuario@ministeriofaro.org"
                                className="login-input"
                            />
                        </motion.div>

                        {/* Password */}
                        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.55 }}>
                            <div className="flex justify-between items-center mb-3 mx-2">
                                <label className="text-[10px] font-black text-gray-400 uppercase tracking-[0.15em]">
                                    Contraseña
                                </label>
                                <Link href="#" className="text-[9px] text-ccf-blue-light font-black uppercase tracking-[0.15em] no-underline">
                                    ¿Olvidaste la clave?
                                </Link>
                            </div>
                            <div className="relative">
                                <input
                                    type={showPassword ? 'text' : 'password'}
                                    required
                                    value={password}
                                    onChange={e => setPassword(e.target.value)}
                                    placeholder="••••••••"
                                    className="login-input pr-[60px]"
                                    style={{ letterSpacing: showPassword ? 'normal' : '0.2em' }}
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    className="absolute right-5 top-1/2 -translate-y-1/2 text-gray-300 bg-transparent border-none cursor-pointer p-0 flex"
                                >
                                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                                </button>
                            </div>
                        </motion.div>

                        {/* Error */}
                        <AnimatePresence>
                            {error && (
                                <motion.div
                                    initial={{ opacity: 0, scale: 0.96 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    exit={{ opacity: 0, scale: 0.96 }}
                                    className="px-6 py-3.5 bg-rose-50 border-2 border-rose-200 rounded-full text-rose-600 text-[11px] font-black text-center uppercase tracking-[0.1em]"
                                >
                                    {error}
                                </motion.div>
                            )}
                        </AnimatePresence>

                        {/* Submit button */}
                        <motion.button
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.65 }}
                            type="submit"
                            disabled={loading}
                            className="login-btn"
                        >
                            {loading ? (
                                <Loader2 className="animate-spin" size={20} />
                            ) : (
                                <>
                                    INGRESAR
                                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M17 8l4 4m0 0l-4 4m4-4H3" />
                                    </svg>
                                </>
                            )}
                        </motion.button>
                    </form>

                    {/* Divider */}
                    <div className="relative my-9">
                        <div className="absolute inset-0 flex items-center">
                            <div className="w-full border-t-2 border-gray-100" />
                        </div>
                        <div className="relative flex justify-center">
                            <span className="bg-white px-4 text-[9px] font-black uppercase tracking-[0.3em] text-gray-300">
                                O bien
                            </span>
                        </div>
                    </div>

                    {/* Google */}
                    <motion.button
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.85 }}
                        type="button"
                        className="login-google-btn mb-10"
                    >
                        <svg width="20" height="20" viewBox="0 0 24 24">
                            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"/>
                            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                        </svg>
                        Google Account
                    </motion.button>

                    {/* Register link */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.95 }}
                        className="text-center"
                    >
                        <p className="text-gray-400 text-[10px] font-bold tracking-[0.15em] uppercase mb-2.5">
                            ¿No tienes una cuenta ministerial?
                        </p>
                        <Link
                            href="/register"
                            className="text-ccf-blue-light font-black text-[10px] uppercase tracking-[0.15em] no-underline"
                        >
                            Solicitar registro ahora
                        </Link>
                    </motion.div>

                </div>
            </motion.section>
        </div>
    );
}
