"use client";

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';

export default function RegisterPage() {
    const [loadingGoogle, setLoadingGoogle] = useState(false);

    const handleGoogleAuth = () => {
        setLoadingGoogle(true);
        window.location.href = '/api/v3/auth/google';
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

                .reg-card {
                    background: rgba(255, 255, 255, 0.05);
                    backdrop-filter: blur(24px);
                    -webkit-backdrop-filter: blur(24px);
                    border: 1px solid rgba(255, 255, 255, 0.12);
                    border-radius: 2rem;
                    box-shadow: 0 40px 100px -20px rgba(0, 0, 0, 0.5),
                                0 0 0 1px rgba(255, 255, 255, 0.05) inset;
                }

                .reg-btn-google {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 14px;
                    width: 100%;
                    background: white;
                    color: rgb(0, 27, 72);
                    border-radius: 9999px;
                    padding: 18px 32px;
                    font-weight: 800;
                    font-size: 13px;
                    text-transform: uppercase;
                    letter-spacing: 0.12em;
                    border: none;
                    cursor: pointer;
                    transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
                    box-shadow: 0 10px 30px -5px rgba(0, 0, 0, 0.3);
                }
                .reg-btn-google:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 15px 35px -5px rgba(0, 0, 0, 0.4);
                    background: #f8fafc;
                }

                .reg-btn-outline {
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    gap: 10px;
                    width: 100%;
                    background: transparent;
                    color: rgba(255, 255, 255, 0.85);
                    border-radius: 9999px;
                    padding: 16px 32px;
                    font-weight: 700;
                    font-size: 12px;
                    text-transform: uppercase;
                    letter-spacing: 0.15em;
                    border: 1.5px solid rgba(255, 255, 255, 0.25);
                    text-decoration: none;
                    transition: all 0.25s ease;
                }
                .reg-btn-outline:hover {
                    background: rgba(255, 255, 255, 0.1);
                    border-color: rgba(255, 255, 255, 0.5);
                    color: white;
                }
            `}</style>

            <div style={{
                display: 'flex', width: '100vw', minHeight: '100vh',
                backgroundColor: 'var(--ccf-blue-dark)',
                alignItems: 'center', justifyContent: 'center',
                padding: '32px 20px', position: 'relative',
            }}>
                <motion.div
                    initial={{ opacity: 0, y: 24 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
                    className="reg-card"
                    style={{ maxWidth: '520px', width: '100%', padding: '56px 44px' }}
                >
                    {/* Header */}
                    <div style={{ textAlign: 'center', marginBottom: '36px' }}>
                        <div style={{
                            display: 'inline-flex', alignItems: 'center', gap: '8px',
                            background: 'rgba(1,138,189,0.15)', border: '1px solid rgba(1,138,189,0.3)',
                            borderRadius: '9999px', padding: '6px 16px', marginBottom: '20px',
                        }}>
                            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--ccf-blue-light)' }} />
                            <span style={{ fontSize: '11px', fontWeight: 800, color: 'var(--ccf-blue-pale)', textTransform: 'uppercase', letterSpacing: '0.15em' }}>
                                Plataforma CCF
                            </span>
                        </div>
                        <h1 style={{ color: 'white', fontSize: '2.2rem', fontWeight: 900, letterSpacing: '-0.03em', margin: '0 0 12px' }}>
                            Crear Cuenta
                        </h1>
                        <p style={{ color: 'rgba(221,232,240,0.7)', fontSize: '0.95rem', lineHeight: 1.6, margin: 0 }}>
                            Accede a la plataforma ministerial, academia y recursos formativos.
                        </p>
                    </div>

                    {/* Google SSO Button */}
                    <div style={{ marginBottom: '32px' }}>
                        <button
                            type="button"
                            onClick={handleGoogleAuth}
                            disabled={loadingGoogle}
                            className="reg-btn-google"
                        >
                            <svg width="20" height="20" viewBox="0 0 24 24">
                                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
                                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
                            </svg>
                            {loadingGoogle ? 'Conectando...' : 'Continuar con Google'}
                        </button>
                    </div>

                    {/* Divider */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '28px' }}>
                        <div style={{ flex: 1, height: '1px', background: 'rgba(255,255,255,0.12)' }} />
                        <span style={{ fontSize: '11px', fontWeight: 800, color: 'rgba(221,232,240,0.4)', textTransform: 'uppercase', letterSpacing: '0.15em' }}>
                            Aprovisionamiento Ministerial
                        </span>
                        <div style={{ flex: 1, height: '1px', background: 'rgba(255,255,255,0.12)' }} />
                    </div>

                    {/* Info Card */}
                    <div style={{
                        background: 'rgba(1,138,189,0.08)',
                        border: '1px solid rgba(1,138,189,0.2)',
                        borderRadius: '1.25rem',
                        padding: '20px 24px',
                        marginBottom: '32px',
                    }}>
                        <p style={{ color: 'rgba(221,232,240,0.85)', fontSize: '0.85rem', lineHeight: 1.6, margin: 0 }}>
                            <strong style={{ color: 'white' }}>¿Tienes una invitación ministerial?</strong> Si eres líder o docente, tu cuenta es aprovisionada por la administración y recibirás un correo de activación con tu enlace seguro.
                        </p>
                    </div>

                    {/* Login Link */}
                    <div style={{ textAlign: 'center' }}>
                        <Link href="/login" className="reg-btn-outline">
                            ¿Ya tienes cuenta? Iniciar Sesión
                        </Link>
                    </div>
                </motion.div>
            </div>
        </>
    );
}
