"use client";

import React, { useState } from 'react';
import Link from 'next/link';
import { Loader2, ArrowLeft, CheckCircle2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { apiFetch } from '@/lib/http';

export default function ForgotPasswordPage() {
    const [email, setEmail] = useState('');
    const [loading, setLoading] = useState(false);
    const [sent, setSent] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        try {
            await apiFetch('/v3/auth/forgot-password', {
                method: 'POST',
                body: { email },
            });
            setSent(true);
        } catch (err: any) {
            setError('No encontramos una cuenta con ese correo o hubo un problema. Intenta de nuevo.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex flex-col md:flex-row w-screen min-h-screen font-sans">

            {/* ── LEFT PANEL: BRANDING ── */}
            <motion.section
                initial={{ opacity: 0, x: -30 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
                className="hidden md:flex md:flex-[1.2] bg-ccf-blue-dark relative flex-col justify-between px-[clamp(40px,8%,90px)] py-[clamp(40px,8%,90px)] min-h-screen overflow-hidden"
            >
                {/* Radial glow */}
                <div
                    className="absolute top-[-20%] right-[-20%] w-[140%] h-[140%] pointer-events-none z-0"
                    style={{ background: 'radial-gradient(circle at 70% 30%, rgba(1,138,189,0.25) 0%, transparent 60%)' }}
                />

                {/* Top badge */}
                <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.4 }}
                    className="relative z-10"
                >
                    <div className="inline-flex items-center gap-3 border border-white/20 rounded-full px-3 py-2.5 bg-white/5 backdrop-blur-md">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
                            <path d="M8 22L10 6L12 2L14 6L16 22H8Z" strokeLinejoin="round"/>
                            <circle cx="12" cy="4" r="1.5" fill="white" stroke="none"/>
                        </svg>
                        <span className="text-white font-bold uppercase tracking-wide text-[10px]">
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
                    <h1 className="font-bold tracking-[-0.04em] leading-[0.88] text-white text-[clamp(3rem,6vw,4.5rem)] m-0">
                        EL <br /> CCF
                    </h1>
                    <p className="text-ccf-blue-light text-[clamp(1rem,2vw,1.25rem)] font-bold tracking-wide uppercase mt-3 leading-[1.4]">
                        Comunidad <br /> Cristiana
                    </p>
                    <div className="w-16 h-1.5 bg-[hsl(var(--bg-primary))] mt-3 rounded-full" />
                </motion.div>

                {/* Bottom motto */}
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 1 }}
                    className="relative z-10"
                >
                    <p className="text-white/90 text-lg font-medium tracking-normal leading-relaxed">
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
                className="flex-1 bg-[hsl(var(--bg-primary))] flex flex-col justify-center px-5 sm:px-[clamp(40px,8%,90px)] py-12 sm:py-[clamp(40px,8%,90px)] min-h-screen"
            >
                <div className="w-full max-w-[420px] mx-auto">

                    {/* Back link */}
                    <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.3 }}
                        className="mb-6"
                    >
                        <Link
                            href="/login"
                            className="inline-flex items-center gap-2 text-[hsl(var(--text-secondary))] hover:text-ccf-blue-dark transition-colors no-underline group"
                        >
                            <ArrowLeft size={14} className="group-hover:-translate-x-0.5 transition-transform" />
                            <span className="text-[9px] font-bold uppercase tracking-wider">Volver al acceso</span>
                        </Link>
                    </motion.div>

                    {/* Header */}
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.4 }}
                        className="mb-6"
                    >
                        <h2 className="text-[clamp(1.75rem,4vw,2.5rem)] font-extrabold text-ccf-blue-dark tracking-[-0.02em] leading-none m-0 mb-3">
                            Recuperar acceso
                        </h2>
                        <p className="text-[hsl(var(--text-secondary))] font-bold uppercase tracking-wide text-[10px] m-0">
                            Restablece tu contraseña por correo
                        </p>
                    </motion.div>

                    <AnimatePresence mode="wait">
                        {sent ? (
                            /* ── SUCCESS STATE ── */
                            <motion.div
                                key="success"
                                initial={{ opacity: 0, scale: 0.96 }}
                                animate={{ opacity: 1, scale: 1 }}
                                className="flex flex-col items-center text-center gap-4 py-6"
                            >
                                <div className="w-14 h-14 rounded-full bg-emerald-50 border-2 border-emerald-200 flex items-center justify-center">
                                    <CheckCircle2 className="text-emerald-500" size={28} />
                                </div>
                                <div>
                                    <p className="text-ccf-blue-dark font-extrabold text-base m-0 mb-1">
                                        Revisa tu correo
                                    </p>
                                    <p className="text-[hsl(var(--text-secondary))] text-[11px] leading-relaxed m-0">
                                        Te enviamos las instrucciones a <strong className="text-ccf-blue-dark">{email}</strong>.
                                        Si no lo ves, revisa la carpeta de spam.
                                    </p>
                                </div>
                                <Link
                                    href="/login"
                                    className="text-ccf-blue-light font-bold text-[10px] uppercase tracking-wider no-underline"
                                >
                                    Volver al inicio de sesión
                                </Link>
                            </motion.div>
                        ) : (
                            /* ── FORM STATE ── */
                            <motion.form
                                key="form"
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                onSubmit={handleSubmit}
                                className="flex flex-col gap-4"
                            >
                                <motion.div
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: 0.5 }}
                                >
                                    <label className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wider block mb-3 ml-2">
                                        Correo electrónico
                                    </label>
                                    <input
                                        type="email"
                                        required
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        placeholder="tu@correo.com"
                                        className="login-input"
                                    />
                                </motion.div>

                                <AnimatePresence>
                                    {error && (
                                        <motion.div
                                            initial={{ opacity: 0, scale: 0.96 }}
                                            animate={{ opacity: 1, scale: 1 }}
                                            exit={{ opacity: 0, scale: 0.96 }}
                                            className="px-3 py-1.5 bg-rose-50 border-2 border-rose-200 rounded-lg text-rose-600 text-[11px] font-bold text-center uppercase tracking-wider"
                                        >
                                            {error}
                                        </motion.div>
                                    )}
                                </AnimatePresence>

                                <motion.button
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: 0.6 }}
                                    type="submit"
                                    disabled={loading}
                                    className="login-btn"
                                >
                                    {loading ? (
                                        <Loader2 className="animate-spin" size={20} />
                                    ) : (
                                        <>
                                            ENVIAR ENLACE SEGURO
                                            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M17 8l4 4m0 0l-4 4m4-4H3" />
                                            </svg>
                                        </>
                                    )}
                                </motion.button>

                                <motion.div
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    transition={{ delay: 0.7 }}
                                    className="text-center"
                                >
                                    <p className="text-[hsl(var(--text-secondary))] text-[10px] font-bold tracking-wider uppercase mb-2">
                                        ¿Recordaste tu clave?
                                    </p>
                                    <Link
                                        href="/login"
                                        className="text-ccf-blue-light font-bold text-[10px] uppercase tracking-wider no-underline"
                                    >
                                        Inicia sesión
                                    </Link>
                                </motion.div>
                            </motion.form>
                        )}
                    </AnimatePresence>

                </div>
            </motion.section>
        </div>
    );
}
