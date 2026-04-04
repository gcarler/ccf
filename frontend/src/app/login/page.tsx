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
        <>
            <style>{`
                :root {
                    --ccf-blue-dark:   rgb(0, 27, 72);
                    --ccf-blue-medium: rgb(0, 69, 129);
                    --ccf-blue-light:  rgb(1, 138, 189);
                    --ccf-blue-pale:   rgb(221, 232, 240);
                }
                html, body { margin: 0; padding: 0; height: 100%; overflow-x: hidden; }

                .input-pill {
                    width: 100%;
                    background-color: #f8fafc;
                    border: 2px solid transparent;
                    border-radius: 9999px;
                    padding: 20px 32px;
                    color: var(--ccf-blue-dark);
                    font-weight: 700;
                    font-size: 1rem;
                    font-family: 'Inter', sans-serif;
                    transition: all 0.3s ease;
                    box-sizing: border-box;
                }
                .input-pill:focus {
                    background-color: white;
                    border-color: var(--ccf-blue-light);
                    outline: none;
                    box-shadow: 0 0 0 4px rgba(1, 138, 189, 0.12);
                }
                .input-pill::placeholder { color: #cbd5e1; font-weight: 500; }

                .btn-pill {
                    background-color: var(--ccf-blue-light);
                    border-radius: 9999px;
                    transition: all 0.3s ease;
                    border: none;
                    cursor: pointer;
                    position: relative;
                    overflow: hidden;
                }
                .btn-pill:hover:not(:disabled) {
                    background-color: var(--ccf-blue-medium);
                    transform: translateY(-2px);
                    box-shadow: 0 10px 25px -5px rgba(1, 138, 189, 0.45);
                }
                .btn-pill:active:not(:disabled) { transform: translateY(0); }
                .btn-pill:disabled { opacity: 0.6; cursor: not-allowed; }

                .google-pill {
                    width: 100%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 12px;
                    border: 2px solid #e5e7eb;
                    padding: 16px 24px;
                    border-radius: 9999px;
                    font-weight: 800;
                    color: #4b5563;
                    font-size: 11px;
                    letter-spacing: 0.15em;
                    text-transform: uppercase;
                    background: white;
                    cursor: pointer;
                    transition: all 0.2s;
                    font-family: 'Inter', sans-serif;
                }
                .google-pill:hover { background-color: #f8fafc; border-color: #d1d5db; }

                .title-heavy {
                    font-weight: 900;
                    letter-spacing: -0.04em;
                    line-height: 0.88;
                }
            `}</style>

            <div style={{ display: 'flex', width: '100vw', minHeight: '100vh', fontFamily: "'Inter', sans-serif" }}>

                {/* ── PANEL IZQUIERDO: IDENTIDAD ── */}
                <motion.section
                    initial={{ opacity: 0, x: -30 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
                    style={{
                        flex: '1.2',
                        backgroundColor: 'var(--ccf-blue-dark)',
                        position: 'relative',
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'space-between',
                        padding: 'clamp(40px, 8%, 90px)',
                        overflow: 'hidden',
                        minHeight: '100vh',
                    }}
                >
                    {/* Radial glow */}
                    <div style={{
                        position: 'absolute', top: '-20%', right: '-20%',
                        width: '140%', height: '140%', pointerEvents: 'none', zIndex: 0,
                        background: 'radial-gradient(circle at 70% 30%, rgba(1,138,189,0.25) 0%, transparent 60%)',
                    }} />

                    {/* Pastilla superior */}
                    <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.4 }}
                        style={{ position: 'relative', zIndex: 10 }}
                    >
                        <div style={{
                            display: 'inline-flex', alignItems: 'center', gap: '12px',
                            border: '1px solid rgba(255,255,255,0.2)',
                            borderRadius: '9999px', padding: '10px 20px',
                            background: 'rgba(255,255,255,0.05)', backdropFilter: 'blur(8px)',
                        }}>
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
                                <path d="M8 22L10 6L12 2L14 6L16 22H8Z" strokeLinejoin="round"/>
                                <circle cx="12" cy="4" r="1.5" fill="white" stroke="none"/>
                            </svg>
                            <span style={{ color: 'white', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.2em', fontSize: '10px' }}>
                                Ministerio Internacional
                            </span>
                        </div>
                    </motion.div>

                    {/* Título EL FARO */}
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.6, duration: 0.8 }}
                        style={{ position: 'relative', zIndex: 10 }}
                    >
                        <h1 className="title-heavy" style={{
                            color: 'white',
                            fontSize: 'clamp(5rem, 10vw, 8rem)',
                            margin: 0,
                        }}>
                            EL <br /> FARO
                        </h1>
                        <p style={{
                            color: 'var(--ccf-blue-light)',
                            fontSize: 'clamp(1rem, 2vw, 1.5rem)',
                            fontWeight: 900,
                            letterSpacing: '0.4em',
                            textTransform: 'uppercase',
                            marginTop: '24px',
                            lineHeight: 1.4,
                        }}>
                            Comunidad <br /> Cristiana
                        </p>
                        <div style={{ width: '64px', height: '6px', backgroundColor: 'white', marginTop: '32px', borderRadius: '999px' }} />
                    </motion.div>

                    {/* Lema inferior */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 1 }}
                        style={{ position: 'relative', zIndex: 10 }}
                    >
                        <p style={{
                            color: 'rgba(221, 232, 240, 0.5)',
                            fontSize: '0.875rem',
                            fontWeight: 700,
                            textTransform: 'uppercase',
                            letterSpacing: '0.1em',
                            lineHeight: 1.9,
                        }}>
                            Guiando a las naciones <br /> hacia la luz de la verdad.
                        </p>
                    </motion.div>

                    {/* Ondas SVG decorativas */}
                    <svg
                        style={{ position: 'absolute', bottom: 0, left: 0, width: '100%', zIndex: 0, pointerEvents: 'none' }}
                        viewBox="0 0 1440 320"
                        preserveAspectRatio="none"
                    >
                        <path fill="rgba(255,255,255,0.03)" d="M0,224L48,213.3C96,203,192,181,288,181.3C384,181,480,203,576,218.7C672,235,768,245,864,240C960,235,1056,213,1152,197.3C1248,181,1344,171,1392,165.3L1440,160L1440,320L1392,320C1344,320,1248,320,1152,320C1056,320,960,320,864,320C768,320,672,320,576,320C480,320,384,320,288,320C192,320,96,320,48,320L0,320Z"/>
                        <path fill="rgba(255,255,255,0.06)" d="M0,128L48,144C96,160,192,192,288,197.3C384,203,480,181,576,160C672,139,768,117,864,128C960,139,1056,181,1152,186.7C1248,192,1344,160,1392,144L1440,128L1440,320L1392,320C1344,320,1248,320,1152,320C1056,320,960,320,864,320C768,320,672,320,576,320C480,320,384,320,288,320C192,320,96,320,48,320L0,320Z"/>
                    </svg>
                </motion.section>

                {/* ── PANEL DERECHO: FORMULARIO ── */}
                <motion.section
                    initial={{ opacity: 0, x: 30 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
                    style={{
                        flex: '1',
                        backgroundColor: 'white',
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'center',
                        padding: 'clamp(40px, 8%, 90px)',
                        minHeight: '100vh',
                    }}
                >
                    <div style={{ width: '100%', maxWidth: '420px', margin: '0 auto' }}>

                        {/* Header del form */}
                        <motion.div
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.3 }}
                            style={{ marginBottom: '56px' }}
                        >
                            <h2 style={{
                                fontSize: 'clamp(2.5rem, 5vw, 3.5rem)',
                                fontWeight: 900,
                                color: 'var(--ccf-blue-dark)',
                                letterSpacing: '-0.04em',
                                lineHeight: 1,
                                margin: 0,
                                marginBottom: '16px',
                            }}>Bienvenido</h2>
                            <p style={{ color: '#9ca3af', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.2em', fontSize: '10px', margin: 0 }}>
                                Acceso a la plataforma digital
                            </p>
                        </motion.div>

                        {/* Formulario */}
                        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>

                            {/* Email */}
                            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.45 }}>
                                <label style={{ fontSize: '10px', fontWeight: 900, color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.15em', display: 'block', marginBottom: '12px', marginLeft: '8px' }}>
                                    Email
                                </label>
                                <input
                                    type="text"
                                    required
                                    value={email}
                                    onChange={e => setEmail(e.target.value)}
                                    placeholder="usuario@ministeriofaro.org"
                                    className="input-pill"
                                />
                            </motion.div>

                            {/* Contraseña */}
                            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.55 }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', marginLeft: '8px', marginRight: '8px' }}>
                                    <label style={{ fontSize: '10px', fontWeight: 900, color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.15em' }}>
                                        Contraseña
                                    </label>
                                    <Link href="#" style={{ fontSize: '9px', color: 'var(--ccf-blue-light)', fontWeight: 900, textTransform: 'uppercase', letterSpacing: '0.15em', textDecoration: 'none' }}>
                                        ¿Olvidaste la clave?
                                    </Link>
                                </div>
                                <div style={{ position: 'relative' }}>
                                    <input
                                        type={showPassword ? 'text' : 'password'}
                                        required
                                        value={password}
                                        onChange={e => setPassword(e.target.value)}
                                        placeholder="••••••••"
                                        className="input-pill"
                                        style={{ paddingRight: '60px', letterSpacing: showPassword ? 'normal' : '0.2em' }}
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowPassword(!showPassword)}
                                        style={{ position: 'absolute', right: '20px', top: '50%', transform: 'translateY(-50%)', color: '#cbd5e1', background: 'none', border: 'none', cursor: 'pointer', padding: 0, display: 'flex' }}
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
                                        style={{
                                            padding: '14px 24px',
                                            backgroundColor: '#fff1f2',
                                            border: '2px solid #fecdd3',
                                            borderRadius: '9999px',
                                            color: '#e11d48',
                                            fontSize: '11px',
                                            fontWeight: 900,
                                            textAlign: 'center',
                                            textTransform: 'uppercase',
                                            letterSpacing: '0.1em',
                                        }}
                                    >
                                        {error}
                                    </motion.div>
                                )}
                            </AnimatePresence>

                            {/* Botón INGRESAR */}
                            <motion.button
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: 0.65 }}
                                type="submit"
                                disabled={loading}
                                className="btn-pill"
                                style={{
                                    width: '100%',
                                    padding: '20px 24px',
                                    color: 'white',
                                    fontWeight: 900,
                                    fontSize: '12px',
                                    textTransform: 'uppercase',
                                    letterSpacing: '0.3em',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    gap: '12px',
                                }}
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

                        {/* Divisor "O bien" */}
                        <div style={{ position: 'relative', margin: '36px 0' }}>
                            <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center' }}>
                                <div style={{ width: '100%', borderTop: '2px solid #f3f4f6' }} />
                            </div>
                            <div style={{ position: 'relative', display: 'flex', justifyContent: 'center' }}>
                                <span style={{ backgroundColor: 'white', padding: '0 16px', fontSize: '9px', fontWeight: 900, textTransform: 'uppercase', letterSpacing: '0.3em', color: '#d1d5db' }}>
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
                            className="google-pill"
                            style={{ marginBottom: '40px' }}
                        >
                            <svg width="20" height="20" viewBox="0 0 24 24">
                                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"/>
                                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                            </svg>
                            Google Account
                        </motion.button>

                        {/* Registro */}
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ delay: 0.95 }}
                            style={{ textAlign: 'center' }}
                        >
                            <p style={{ color: '#9ca3af', fontSize: '10px', fontWeight: 700, letterSpacing: '0.15em', textTransform: 'uppercase', marginBottom: '10px' }}>
                                ¿No tienes una cuenta ministerial?
                            </p>
                            <Link
                                href="/register"
                                style={{ color: 'var(--ccf-blue-light)', fontWeight: 900, fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.15em', textDecoration: 'none' }}
                            >
                                Solicitar registro ahora
                            </Link>
                        </motion.div>

                    </div>
                </motion.section>
            </div>
        </>
    );
}
