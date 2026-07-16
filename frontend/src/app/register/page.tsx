"use client";

import React, { useState } from 'react';
import { apiFetch } from '@/lib/http';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2, Eye, EyeOff } from 'lucide-react';
import Link from 'next/link';

export default function RegisterPage() {
    const [formData, setFormData] = useState({
        full_name: '',
        email: '',
        password: '',
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
            await apiFetch('/v3/auth/register', {
                method: 'POST',
                body: {
                    username: formData.email,
                    email: formData.email,
                    password: formData.password,
                    full_name: formData.full_name,
                    role: 'estudiante',
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
            <>
                <style>{`
                    :root {
                        --ccf-blue-dark:   rgb(0, 27, 72);
                        --ccf-blue-medium: rgb(0, 69, 129);
                        --ccf-blue-light:  rgb(1, 138, 189);
                        --ccf-blue-pale:   rgb(221, 232, 240);
                    }
                    html, body { margin: 0; padding: 0; height: 100%; overflow-x: hidden; }
                `}</style>
                <div style={{
                    display: 'flex', width: '100vw', minHeight: '100vh',
                    alignItems: 'center', justifyContent: 'center',
                    backgroundColor: 'var(--ccf-blue-dark)',
                }}>
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        style={{
                            background: 'rgba(255,255,255,0.06)',
                            border: '1px solid rgba(255,255,255,0.12)',
                            borderRadius: '2rem', padding: '64px 56px',
                            textAlign: 'center', maxWidth: '480px', width: '100%',
                        }}
                    >
                        <div style={{
                            width: '72px', height: '72px', borderRadius: '50%',
                            background: 'rgba(1,138,189,0.2)', display: 'flex',
                            alignItems: 'center', justifyContent: 'center', margin: '0 auto 32px',
                        }}>
                            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="rgb(1,138,189)" strokeWidth="2.5">
                                <rect x="2" y="4" width="20" height="16" rx="2" strokeLinecap="round" strokeLinejoin="round"/>
                                <path d="M22 6L12 13 2 6" strokeLinecap="round" strokeLinejoin="round"/>
                            </svg>
                        </div>
                        <h2 style={{ color: 'white', fontSize: '2rem', fontWeight: 900, letterSpacing: '-0.04em', margin: '0 0 16px' }}>
                            ¡Cuenta creada!
                        </h2>
                        <p style={{ color: 'rgba(221,232,240,0.6)', fontSize: '0.95rem', lineHeight: 1.7, marginBottom: '24px' }}>
                            Te enviamos un correo de verificación. Revisa tu bandeja de entrada y haz clic en el enlace para activar tu cuenta.
                        </p>
                        <p style={{ color: 'rgba(221,232,240,0.4)', fontSize: '0.8rem', lineHeight: 1.5, marginBottom: '40px' }}>
                            ¿No lo recibiste? Revisa la carpeta de spam o intenta registrarte de nuevo.
                        </p>
                        <Link
                            href="/login"
                            style={{
                                display: 'inline-flex', alignItems: 'center', gap: '10px',
                                backgroundColor: 'var(--ccf-blue-light)', color: 'white',
                                borderRadius: '9999px', padding: '18px 40px',
                                fontWeight: 900, fontSize: '11px', textTransform: 'uppercase',
                                letterSpacing: '0.25em', textDecoration: 'none',
                            }}
                        >
                            Ir al ingreso
                            <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M17 8l4 4m0 0l-4 4m4-4H3" />
                            </svg>
                        </Link>
                    </motion.div>
                </div>
            </>
        );
    }

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

                .reg-input-pill {
                    width: 100%;
                    background-color: #f8fafc;
                    border: 2px solid transparent;
                    border-radius: 9999px;
                    padding: 20px 32px;
                    color: var(--ccf-blue-dark);
                    font-weight: 700;
                    font-size: 1rem;
                    transition: all 0.3s ease;
                    box-sizing: border-box;
                }
                .reg-input-pill:focus {
                    background-color: white;
                    border-color: var(--ccf-blue-light);
                    outline: none;
                    box-shadow: 0 0 0 4px rgba(1, 138, 189, 0.12);
                }
                .reg-input-pill::placeholder { color: #cbd5e1; font-weight: 500; }

                .reg-btn-pill {
                    background-color: var(--ccf-blue-light);
                    border-radius: 9999px;
                    transition: all 0.3s ease;
                    border: none;
                    cursor: pointer;
                    position: relative;
                    overflow: hidden;
                }
                .reg-btn-pill:hover:not(:disabled) {
                    background-color: var(--ccf-blue-medium);
                    transform: translateY(-2px);
                    box-shadow: 0 10px 25px -5px rgba(1, 138, 189, 0.45);
                }
                .reg-btn-pill:active:not(:disabled) { transform: translateY(0); }
                .reg-btn-pill:disabled { opacity: 0.6; cursor: not-allowed; }

                .title-heavy {
                    font-weight: 900;
                    letter-spacing: -0.04em;
                    line-height: 0.88;
                }
            `}</style>

            <div style={{ display: 'flex', width: '100vw', minHeight: '100vh' }}>

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

                    {/* Título CCF */}
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
                            EL <br /> CCF
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

                        {/* Volver al login */}
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ delay: 0.2 }}
                            style={{ marginBottom: '32px' }}
                        >
                            <Link
                                href="/login"
                                style={{
                                    display: 'inline-flex', alignItems: 'center', gap: '8px',
                                    color: '#9ca3af', fontSize: '10px', fontWeight: 900,
                                    textTransform: 'uppercase', letterSpacing: '0.15em',
                                    textDecoration: 'none', transition: 'color 0.2s',
                                }}
                            >
                                <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M7 16l-4-4m0 0l4-4m-4 4h18" />
                                </svg>
                                Regresar al acceso
                            </Link>
                        </motion.div>

                        {/* Header del form */}
                        <motion.div
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.3 }}
                            style={{ marginBottom: '48px' }}
                        >
                            <h2 style={{
                                fontSize: 'clamp(2.2rem, 5vw, 3rem)',
                                fontWeight: 900,
                                color: 'var(--ccf-blue-dark)',
                                letterSpacing: '-0.04em',
                                lineHeight: 1,
                                margin: 0,
                                marginBottom: '16px',
                            }}>Crear cuenta</h2>
                            <p style={{ color: '#9ca3af', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.2em', fontSize: '10px', margin: 0 }}>
                                Registro ministerial
                            </p>
                        </motion.div>

                        {/* Formulario */}
                        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>

                            {/* Nombre */}
                            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}>
                                <label style={{ fontSize: '10px', fontWeight: 900, color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.15em', display: 'block', marginBottom: '12px', marginLeft: '8px' }}>
                                    Nombre completo
                                </label>
                                <input
                                    type="text"
                                    required
                                    value={formData.full_name}
                                    onChange={e => setFormData({ ...formData, full_name: e.target.value })}
                                    placeholder="Juan Pérez"
                                    className="reg-input-pill"
                                />
                            </motion.div>

                            {/* Email */}
                            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.48 }}>
                                <label style={{ fontSize: '10px', fontWeight: 900, color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.15em', display: 'block', marginBottom: '12px', marginLeft: '8px' }}>
                                    Correo ministerial
                                </label>
                                <input
                                    type="email"
                                    required
                                    value={formData.email}
                                    onChange={e => setFormData({ ...formData, email: e.target.value })}
                                    placeholder="correo@ejemplo.com"
                                    className="reg-input-pill"
                                />
                            </motion.div>

                            {/* Contraseña */}
                            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.56 }}>
                                <label style={{ fontSize: '10px', fontWeight: 900, color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.15em', display: 'block', marginBottom: '12px', marginLeft: '8px' }}>
                                    Contraseña
                                </label>
                                <div style={{ position: 'relative' }}>
                                    <input
                                        type={showPassword ? 'text' : 'password'}
                                        required
                                        minLength={6}
                                        value={formData.password}
                                        onChange={e => setFormData({ ...formData, password: e.target.value })}
                                        placeholder="••••••••"
                                        className="reg-input-pill"
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

                            {/* Rol fijo */}
                            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.62 }}>
                                <div style={{
                                    padding: '16px 24px', borderRadius: '9999px',
                                    background: 'rgba(1,138,189,0.06)',
                                    border: '2px solid rgba(1,138,189,0.15)',
                                    display: 'flex', alignItems: 'center', gap: '12px',
                                }}>
                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--ccf-blue-light)" strokeWidth="2.5">
                                        <circle cx="12" cy="12" r="10"/><path d="M12 8v4l3 3"/>
                                    </svg>
                                    <div>
                                        <span style={{ fontSize: '10px', fontWeight: 900, color: 'var(--ccf-blue-light)', textTransform: 'uppercase', letterSpacing: '0.15em' }}>
                                            Rol: Estudiante
                                        </span>
                                        <p style={{ margin: 0, fontSize: '10px', color: '#9ca3af', marginTop: '2px' }}>
                                            Acceso estándar a academia y recursos.
                                        </p>
                                    </div>
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

                            {/* Botón CREAR CUENTA */}
                            <motion.button
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: 0.7 }}
                                type="submit"
                                disabled={loading}
                                className="reg-btn-pill"
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
                                        Crear cuenta ahora
                                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M17 8l4 4m0 0l-4 4m4-4H3" />
                                        </svg>
                                    </>
                                )}
                            </motion.button>
                        </form>

                        {/* Link de ingreso */}
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ delay: 0.9 }}
                            style={{ textAlign: 'center', marginTop: '36px' }}
                        >
                            <p style={{ color: '#9ca3af', fontSize: '10px', fontWeight: 700, letterSpacing: '0.15em', textTransform: 'uppercase', marginBottom: '10px' }}>
                                ¿Ya tienes una cuenta ministerial?
                            </p>
                            <Link
                                href="/login"
                                style={{ color: 'var(--ccf-blue-light)', fontWeight: 900, fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.15em', textDecoration: 'none' }}
                            >
                                Inicia sesión ahora
                            </Link>
                        </motion.div>

                    </div>
                </motion.section>
            </div>
        </>
    );
}
