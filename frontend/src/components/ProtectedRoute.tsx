"use client";

import React, { useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/navigation';
import { SITE_NAME } from '@/lib/site-config';

interface ProtectedRouteProps {
    children: React.ReactNode;
    allowedRoles?: string[];
    allowedPermissions?: string[];
    requireVerifiedEmail?: boolean;
}

// ─── Icono de llama del brand (igual que el login) ───────────────────────────
function FaroFlame({ size = 16 }: { size?: number }) {
    return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
            <path d="M8 22L10 6L12 2L14 6L16 22H8Z" strokeLinejoin="round" />
            <circle cx="12" cy="4" r="1.5" fill="white" stroke="none" />
        </svg>
    );
}

// ─── Pantalla de bloqueo ──────────────────────────────────────────────────────

type GateVariant = 'lock' | 'shield' | 'key';

function GateScreen({
    variant = 'lock',
    title,
    message,
    href,
    cta,
}: {
    variant?: GateVariant;
    title: string;
    message: string;
    href: string;
    cta: string;
}) {
    const isWarning = variant !== 'lock';

    // Colores del brand CCF
    const teal = 'rgb(1, 138, 189)';       // ccf-blue-light
    const navy = 'rgb(0, 27, 72)';          // ccf-blue-dark
    const warnColor = '#f59e0b';

    const accentColor = isWarning ? warnColor : teal;
    const accentRgb = isWarning ? '245,158,11' : '1,138,189';

    const LockIcon = () => (
        <svg width="36" height="36" viewBox="0 0 24 24" fill="none" strokeLinecap="round" strokeLinejoin="round">
            <defs>
                <linearGradient id="iconGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor={isWarning ? '#fbbf24' : '#67e8f9'} />
                    <stop offset="100%" stopColor={accentColor} />
                </linearGradient>
            </defs>
            {variant === 'lock' && (
                <>
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2" stroke="url(#iconGrad)" strokeWidth="1.5" />
                    <path d="M7 11V7a5 5 0 0 1 10 0v4" stroke="url(#iconGrad)" strokeWidth="1.5" />
                    <circle cx="12" cy="16" r="1.2" fill="url(#iconGrad)" />
                </>
            )}
            {variant === 'shield' && (
                <>
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" stroke="url(#iconGrad)" strokeWidth="1.5" />
                    <line x1="12" y1="9" x2="12" y2="13" stroke="url(#iconGrad)" strokeWidth="1.5" />
                    <circle cx="12" cy="16" r="0.8" fill="url(#iconGrad)" />
                </>
            )}
            {variant === 'key' && (
                <>
                    <circle cx="8" cy="8" r="5" stroke="url(#iconGrad)" strokeWidth="1.5" />
                    <path d="M21 21l-9.1-9.1" stroke="url(#iconGrad)" strokeWidth="1.5" />
                    <path d="M15 17l2 2 2-2" stroke="url(#iconGrad)" strokeWidth="1.5" />
                </>
            )}
        </svg>
    );

    return (
        <div
            className="relative flex h-screen w-full items-center justify-center overflow-hidden"
            style={{ background: `linear-gradient(160deg, #0a1628 0%, #001b48 50%, #0d1f3c 100%)` }}
        >
            {/* Glow radial — mismo que el login left panel */}
            <div
                className="absolute top-[-20%] right-[-20%] w-[140%] h-[140%] pointer-events-none"
                style={{
                    background: `radial-gradient(circle at 70% 30%, rgba(${accentRgb},0.18) 0%, transparent 60%)`,
                }}
            />
            {/* Glow secundario abajo-izquierda */}
            <div
                className="absolute bottom-[-10%] left-[-10%] w-[80%] h-[80%] pointer-events-none"
                style={{
                    background: `radial-gradient(circle at 20% 80%, rgba(0,69,129,0.3) 0%, transparent 60%)`,
                }}
            />

            {/* Contenido */}
            <div className="relative z-10 flex flex-col items-center w-full px-6" style={{ maxWidth: '400px' }}>

                {/* Badge del brand — idéntico al login */}
                <div className="inline-flex items-center gap-3 border border-white/20 rounded-full px-3 py-2.5 bg-white/5 backdrop-blur-md mb-10">
                    <FaroFlame size={16} />
                    <span className="text-white font-bold uppercase tracking-wide text-[10px]">
                        Ministerio Internacional
                    </span>
                </div>

                {/* Ícono principal — grande e impactante */}
                <div className="relative flex items-center justify-center mb-8">
                    {/* Anillo exterior pulsante */}
                    <div
                        className="absolute rounded-full animate-ping"
                        style={{
                            width: '120px', height: '120px',
                            border: `1px solid rgba(${accentRgb},0.2)`,
                            animationDuration: '2.5s',
                        }}
                    />
                    {/* Anillo medio */}
                    <div
                        className="absolute rounded-full"
                        style={{
                            width: '96px', height: '96px',
                            border: `1px solid rgba(${accentRgb},0.25)`,
                        }}
                    />
                    {/* Círculo principal */}
                    <div
                        className="relative flex items-center justify-center"
                        style={{
                            width: '72px', height: '72px',
                            borderRadius: '50%',
                            background: `radial-gradient(circle at 35% 35%, rgba(${accentRgb},0.25) 0%, rgba(${accentRgb},0.08) 100%)`,
                            border: `1.5px solid rgba(${accentRgb},0.5)`,
                            boxShadow: `0 0 40px rgba(${accentRgb},0.25), 0 0 80px rgba(${accentRgb},0.1), inset 0 1px 0 rgba(255,255,255,0.08)`,
                        }}
                    >
                        <LockIcon />
                    </div>
                </div>

                {/* Título */}
                <h2
                    className="font-extrabold tracking-tight text-center m-0 mb-3"
                    style={{
                        fontSize: 'clamp(1.6rem, 5vw, 2rem)',
                        background: 'linear-gradient(to bottom, rgba(255,255,255,1) 0%, rgba(255,255,255,0.6) 100%)',
                        WebkitBackgroundClip: 'text',
                        WebkitTextFillColor: 'transparent',
                        lineHeight: 1.1,
                    }}
                >
                    {title}
                </h2>

                {/* Mensaje */}
                <p
                    className="text-sm leading-relaxed text-center mb-8"
                    style={{ color: 'rgba(255,255,255,0.4)', maxWidth: '280px' }}
                >
                    {message}
                </p>

                {/* Línea separadora con gradiente */}
                <div
                    className="w-full mb-8"
                    style={{
                        height: '1px',
                        background: `linear-gradient(to right, transparent, rgba(${accentRgb},0.3), transparent)`,
                    }}
                />

                {/* Botón CTA */}
                <a
                    href={href}
                    className="group w-full flex items-center justify-center gap-3 py-3.5 px-6 rounded-xl font-bold text-sm text-white no-underline"
                    style={{
                        background: isWarning
                            ? 'linear-gradient(135deg, #b45309 0%, #d97706 100%)'
                            : `linear-gradient(135deg, ${navy} 0%, rgb(0,69,129) 50%, ${teal} 100%)`,
                        border: `1px solid rgba(${accentRgb},0.35)`,
                        boxShadow: `0 4px 24px rgba(${accentRgb},0.25), inset 0 1px 0 rgba(255,255,255,0.1)`,
                        transition: 'opacity 0.15s, transform 0.1s',
                    }}
                    onMouseEnter={e => { (e.currentTarget as HTMLElement).style.opacity = '0.88'; }}
                    onMouseLeave={e => { (e.currentTarget as HTMLElement).style.opacity = '1'; }}
                >
                    <span className="uppercase tracking-wider text-[11px]">{cta}</span>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"
                        style={{ transition: 'transform 0.15s' }}
                        className="group-hover:translate-x-0.5">
                        <path d="M5 12h14M12 5l7 7-7 7" />
                    </svg>
                </a>

                {/* Footer */}
                <p
                    className="mt-6 text-[10px] font-medium tracking-[0.18em] uppercase"
                    style={{ color: 'rgba(255,255,255,0.18)' }}
                >
                    {SITE_NAME} · Acceso Protegido
                </p>
            </div>

            {/* Ondas decorativas — idénticas al login */}
            <svg
                className="absolute bottom-0 left-0 w-full pointer-events-none"
                viewBox="0 0 1440 180"
                preserveAspectRatio="none"
                style={{ height: '120px' }}
            >
                <path fill="rgba(255,255,255,0.02)"
                    d="M0,96L48,90C96,85,192,74,288,74C384,74,480,85,576,90C672,96,768,96,864,90C960,85,1056,74,1152,74C1248,74,1344,85,1392,90L1440,96L1440,180L0,180Z" />
                <path fill="rgba(255,255,255,0.04)"
                    d="M0,128L48,117C96,107,192,85,288,80C384,75,480,85,576,90C672,96,768,107,864,112C960,117,1056,117,1152,107C1248,96,1344,80,1392,72L1440,64L1440,180L0,180Z" />
            </svg>
        </div>
    );
}

// ─── Pantalla de carga ────────────────────────────────────────────────────────

function LoadingScreen() {
    return (
        <div
            className="relative flex h-screen w-full items-center justify-center overflow-hidden"
            style={{ background: 'linear-gradient(160deg, #0a1628 0%, #001b48 50%, #0d1f3c 100%)' }}
        >
            <div
                className="absolute top-[-20%] right-[-20%] w-[140%] h-[140%] pointer-events-none"
                style={{ background: 'radial-gradient(circle at 70% 30%, rgba(1,138,189,0.12) 0%, transparent 60%)' }}
            />

            <div className="relative z-10 flex flex-col items-center gap-5">
                {/* Badge */}
                <div className="inline-flex items-center gap-2.5 border border-white/15 rounded-full px-3 py-2 bg-white/5 backdrop-blur-md mb-2">
                    <FaroFlame size={14} />
                    <span className="text-white/60 font-bold uppercase tracking-wide text-[9px]">{SITE_NAME}</span>
                </div>

                {/* Spinner */}
                <div className="relative w-14 h-14">
                    <div
                        className="absolute inset-0 rounded-full animate-spin"
                        style={{
                            background: 'conic-gradient(from 0deg, transparent 75%, rgb(1,138,189))',
                            WebkitMask: 'radial-gradient(circle, transparent 58%, black 59%)',
                            mask: 'radial-gradient(circle, transparent 58%, black 59%)',
                        }}
                    />
                    <div
                        className="absolute inset-2 rounded-full"
                        style={{
                            background: 'radial-gradient(circle at 35% 35%, rgba(1,138,189,0.15) 0%, rgba(0,27,72,0.5) 100%)',
                            border: '1px solid rgba(1,138,189,0.2)',
                        }}
                    />
                </div>

                <p
                    className="text-[10px] font-bold tracking-[0.25em] uppercase animate-pulse"
                    style={{ color: 'rgba(255,255,255,0.25)' }}
                >
                    Verificando acceso
                </p>
            </div>

            {/* Ondas */}
            <svg className="absolute bottom-0 left-0 w-full pointer-events-none" viewBox="0 0 1440 180"
                preserveAspectRatio="none" style={{ height: '100px' }}>
                <path fill="rgba(255,255,255,0.02)"
                    d="M0,96L48,90C96,85,192,74,288,74C384,74,480,85,576,90C672,96,768,96,864,90C960,85,1056,74,1152,74C1248,74,1344,85,1392,90L1440,96L1440,180L0,180Z" />
            </svg>
        </div>
    );
}

// ─── Componente principal ─────────────────────────────────────────────────────

export default function ProtectedRoute({ children, allowedRoles, allowedPermissions }: ProtectedRouteProps) {
    const { user, isAuthenticated, loading, hasPermission } = useAuth();
    const router = useRouter();

    useEffect(() => {
        const hasToken = typeof window !== 'undefined' && (!!sessionStorage.getItem('ccf_token') || !!localStorage.getItem('ccf_token'));

        if (!loading) {
            if (!isAuthenticated && !hasToken) {
                console.warn("[AUTH QUALITY] No user and no token found. Redirecting to login.");
                router.push('/login');
            } else if (isAuthenticated && user) {
                if (allowedRoles) {
                    const normalizedUserRole = user.role.toLowerCase();
                    const normalizedAllowedRoles = allowedRoles.map(r => r.toLowerCase());
                    if (!normalizedAllowedRoles.includes(normalizedUserRole)) {
                        console.warn(`[AUTH QUALITY] Role mismatch: ${normalizedUserRole} not in ${normalizedAllowedRoles}. Redirecting.`);
                        if (['admin', 'coordinador', 'docente'].includes(normalizedUserRole)) {
                            router.push('/plataforma/admin');
                        } else {
                            router.push('/plataforma/academy');
                        }
                        return;
                    }
                }
                if (allowedPermissions) {
                    const hasAny = allowedPermissions.some(p => hasPermission(p));
                    if (!hasAny) {
                        console.warn(`[AUTH QUALITY] No required permissions ${allowedPermissions}. Redirecting.`);
                        router.push('/plataforma/academy');
                    }
                }
            }
        }
    }, [isAuthenticated, loading, user, allowedRoles, allowedPermissions, hasPermission, router]);

    if (loading) return <LoadingScreen />;

    if (!isAuthenticated) {
        return (
            <GateScreen
                variant="lock"
                title="Acceso Restringido"
                message="Esta sección requiere autenticación. Inicia sesión con tus credenciales para continuar."
                href="/login"
                cta="Iniciar Sesión"
            />
        );
    }

    if (allowedRoles && user && !allowedRoles.includes(user.role)) {
        return (
            <GateScreen
                variant="shield"
                title="Sin Permisos"
                message="Este módulo requiere rol pastoral o administrativo. Contacta al administrador si crees que es un error."
                href="/plataforma/admin"
                cta="Volver al Inicio"
            />
        );
    }

    if (allowedPermissions && user && !allowedPermissions.some(p => hasPermission(p))) {
        return (
            <GateScreen
                variant="key"
                title="Permiso Denegado"
                message="No tienes los permisos necesarios para acceder a esta sección."
                href="/plataforma/admin"
                cta="Volver al Inicio"
            />
        );
    }

    return <>{children}</>;
}
