"use client";

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import {
    Award,
    Crown,
    Star,
    Zap,
    Shield,
    ChevronRight,
    Edit3,
    Heart,
    User,
    Settings,
    Loader2,
    AlertCircle,
    Instagram,
    Facebook,
    Twitter
} from 'lucide-react';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';

interface Position {
    id: number;
    position_name: string;
    category: string | null;
    is_active: boolean;
    start_date: string | null;
    end_date: string | null;
}

interface Badge {
    id: number;
    name: string;
    description: string | null;
    icon_key: string;
    xp_reward: number;
    earned_at: string | null;
}

interface PersonaInfo {
    id: string | null;
    nombre_completo?: string;
    first_name?: string;
    last_name?: string;
    church_role: string | null;
    spiritual_status: string | null;
    registration_date: string | null;
    bio_short?: string | null;
    social_instagram?: string | null;
    social_facebook?: string | null;
    social_twitter?: string | null;
}

interface LevelInfo {
    title: string | null;
    min_xp: number;
    icon_key: string | null;
    next_title: string | null;
    next_min_xp: number | null;
}

interface ProfileData {
    persona?: PersonaInfo;
    id?: string | null;
    first_name?: string;
    last_name?: string;
    nombre_completo?: string;
    church_role?: string | null;
    spiritual_status?: string | null;
    registration_date?: string | null;
    bio_short?: string | null;
    social_instagram?: string | null;
    social_facebook?: string | null;
    social_twitter?: string | null;
    positions?: Position[];
    skills?: string[];
    badges?: Badge[];
    xp?: number;
    level?: LevelInfo;
}

const BADGE_ICONS: Record<string, React.ComponentType<any>> = {
    star: Star,
    heart: Heart,
    shield: Shield,
    award: Award,
    crown: Crown,
    zap: Zap,
};

function badgeIcon(iconKey: string | null) {
    const key = iconKey?.toLowerCase() || '';
    return BADGE_ICONS[key] || Award;
}

export default function MinistryProfilePage() {
    const { token } = useAuth();
    const [profile, setProfile] = useState<ProfileData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!token) return;
        apiFetch<ProfileData>('/crm/personas/me/profile', { token })
            .then(data => setProfile(data))
            .catch(err => {
                const msg = (err as any)?.detail?.detail || 'No se pudo cargar el perfil ministerial';
                setError(msg);
            })
            .finally(() => setLoading(false));
    }, [token]);

    const sidebarSections = [
        {
            title: 'Cuenta',
            items: [
                { id: 'account-profile', label: 'Mi Perfil', href: '/plataforma/account', icon: User },
                { id: 'account-ministry', label: 'Perfil Ministerial', href: '/plataforma/account/ministry-profile', icon: Crown },
                { id: 'settings-general', label: 'Configuración', href: '/plataforma/settings', icon: Settings },
            ]
        }
    ];

    if (loading) {
        return (
            <WorkspaceLayout sidebarTitle="Cuenta" sidebarSections={sidebarSections}>
                <div className="p-4 flex items-center justify-center min-h-[60vh]">
                    <Loader2 className="animate-spin text-[hsl(var(--warning))]" size={32} />
                </div>
            </WorkspaceLayout>
        );
    }

    if (error || !profile) {
        return (
            <WorkspaceLayout sidebarTitle="Cuenta" sidebarSections={sidebarSections}>
                <div className="p-4 flex flex-col items-center justify-center min-h-[60vh] gap-3">
                    <AlertCircle size={40} className="text-[hsl(var(--warning))/0.6]" />
                    <p className="text-[hsl(var(--text-secondary))] text-sm text-center">{error || 'Perfil no disponible'}</p>
                </div>
            </WorkspaceLayout>
        );
    }

    const persona: PersonaInfo = profile.persona || {
        id: profile.id ?? null,
        first_name: profile.first_name,
        last_name: profile.last_name,
        nombre_completo: profile.nombre_completo,
        church_role: profile.church_role ?? null,
        spiritual_status: profile.spiritual_status ?? null,
        registration_date: profile.registration_date ?? null,
        bio_short: profile.bio_short ?? null,
        social_instagram: profile.social_instagram ?? null,
        social_facebook: profile.social_facebook ?? null,
        social_twitter: profile.social_twitter ?? null,
    };
    const bioShort = persona.bio_short ?? profile.bio_short;
    const socialInstagram = persona.social_instagram ?? profile.social_instagram;
    const socialFacebook = persona.social_facebook ?? profile.social_facebook;
    const socialTwitter = persona.social_twitter ?? profile.social_twitter;
    const positions = profile.positions || [];
    const skills = profile.skills || [];
    const badges = profile.badges || [];
    const xp = profile.xp || 0;
    const level = profile.level || { title: 'Servidor', min_xp: 0, icon_key: null, next_title: null, next_min_xp: 1000 };

    const initials = (persona.nombre_completo?.charAt(0) ?? persona.first_name?.charAt(0) ?? '').toUpperCase();
    const fullName = persona.nombre_completo || `${persona.first_name ?? ''} ${persona.last_name ?? ''}`.trim() || 'Persona';
    const statusLabel = persona.spiritual_status || persona.church_role || 'Persona';
    const sinceYear = persona.registration_date
        ? new Date(persona.registration_date).getFullYear()
        : null;

    // XP progress
    const xpCurrent = xp;
    const xpMin = level.min_xp || 0;
    const xpMax = level.next_min_xp || xpMin + 1000;
    const xpProgress = xpMax > xpMin ? Math.min((xpCurrent - xpMin) / (xpMax - xpMin) * 100, 100) : 0;
    const xpRemaining = xpMax - xpCurrent;
    const levelTitle = level.title || '—';
    const nextLevelTitle = level.next_title || 'Siguiente nivel';

    return (
        <WorkspaceLayout sidebarTitle="Cuenta" sidebarSections={sidebarSections}>
            <div className="p-4 space-y-3 animate-in fade-in duration-1000">
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-3">
                <div className="space-y-2">
                    <div className="inline-flex items-center gap-2 px-3 py-1 bg-[hsl(var(--warning)/0.1)] text-[hsl(var(--warning))] rounded-full text-2xs font-semibold uppercase tracking-wide w-fit">
                        <Crown size={12} /> Mi Identidad en el Reino
                    </div>
                    <h1 className="text-lg font-bold tracking-tighter text-[hsl(var(--text-primary))] uppercase italic">
                        Perfil <span className="text-[hsl(var(--warning))]">Ministerial</span>
                    </h1>
                    <p className="text-[hsl(var(--text-secondary))] text-sm max-w-xl">
                        Gestiona tus dones, habilidades y oficios eclesiásticos. Tu llamado es nuestra prioridad.
                    </p>
                </div>

                <Link
                    href="/plataforma/account"
                    className="px-3 py-2 bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] hover:bg-[hsl(var(--surface-3))] text-[hsl(var(--text-primary))] text-2xs font-semibold uppercase tracking-wide rounded-lg transition-all flex items-center gap-2 shrink-0"
                >
                    <Edit3 size={16} /> Editar Perfil
                </Link>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
                <div className="lg:col-span-2 space-y-3">
                    <div className="bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] p-4 rounded-lg space-y-3">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                            <div className="flex items-center gap-3">
                                <div className="w-20 h-20 sm:w-24 sm:h-24 bg-gradient-to-br from-[hsl(var(--warning))] to-[hsl(var(--primary))] rounded-lg flex items-center justify-center text-[hsl(var(--primary-foreground))] text-3xl font-bold shadow-2xl shrink-0">
                                    {initials || '?'}
                                </div>
                                <div className="space-y-1">
                                    <h2 className="text-xl font-bold text-[hsl(var(--text-primary))] tracking-tight uppercase italic">{fullName}</h2>
                                    <div className="flex items-center gap-2 text-2xs text-[hsl(var(--text-secondary))] font-semibold uppercase tracking-wide">
                                        <Shield size={12} className="text-[hsl(var(--warning))]" /> {statusLabel}
                                        {sinceYear && <><span className="opacity-20">•</span> Desde {sinceYear}</>}
                                    </div>
                                    {/* Redes Sociales Pastorales */}
                                    {(socialInstagram || socialFacebook || socialTwitter) && (
                                        <div className="flex items-center gap-2 pt-1.5">
                                            {socialInstagram && (
                                                <a
                                                    href={socialInstagram}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="p-1.5 rounded-md bg-[hsl(var(--surface-2))] hover:bg-[hsl(var(--surface-3))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] border border-[hsl(var(--border))] transition-colors"
                                                    title="Instagram"
                                                    aria-label="Instagram"
                                                >
                                                    <Instagram size={14} />
                                                </a>
                                            )}
                                            {socialFacebook && (
                                                <a
                                                    href={socialFacebook}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="p-1.5 rounded-md bg-[hsl(var(--surface-2))] hover:bg-[hsl(var(--surface-3))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] border border-[hsl(var(--border))] transition-colors"
                                                    title="Facebook"
                                                    aria-label="Facebook"
                                                >
                                                    <Facebook size={14} />
                                                </a>
                                            )}
                                            {socialTwitter && (
                                                <a
                                                    href={socialTwitter}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="p-1.5 rounded-md bg-[hsl(var(--surface-2))] hover:bg-[hsl(var(--surface-3))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] border border-[hsl(var(--border))] transition-colors"
                                                    title="X (Twitter)"
                                                    aria-label="X (Twitter)"
                                                >
                                                    <Twitter size={14} />
                                                </a>
                                            )}
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* Biografía Breve Ministerial */}
                        {bioShort && (
                            <div className="p-3.5 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] space-y-1">
                                <span className="text-2xs font-semibold text-[hsl(var(--warning))] uppercase tracking-wide flex items-center gap-1.5">
                                    <Crown size={12} /> Biografía Ministerial
                                </span>
                                <p className="text-xs text-[hsl(var(--text-secondary))] leading-relaxed font-medium">
                                    {bioShort}
                                </p>
                            </div>
                        )}

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-8 border-t border-[hsl(var(--border))]">
                            <div className="space-y-4">
                                <h3 className="text-xs font-semibold text-[hsl(var(--text-primary))] uppercase tracking-wide flex items-center gap-2">
                                    <Crown size={14} className="text-[hsl(var(--warning))]" /> Oficios Eclesiásticos
                                </h3>
                                <div className="space-y-2">
                                    {positions.length === 0 ? (
                                        <p className="text-2xs text-[hsl(var(--text-secondary))] italic">Sin oficios registrados</p>
                                    ) : positions.filter(p => p.is_active).map((pos) => (
                                        <div key={pos.id} className="flex items-center gap-3 bg-[hsl(var(--surface-2))] p-3 rounded-md border border-[hsl(var(--border))]">
                                            <div className="w-2 h-2 rounded-full bg-[hsl(var(--warning))] shadow-[hsl(var(--warning)/0.4)]" />
                                            <span className="text-sm font-bold text-[hsl(var(--text-primary))] uppercase tracking-tight">{pos.position_name}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                            <div className="space-y-4">
                                <h3 className="text-xs font-semibold text-[hsl(var(--text-primary))] uppercase tracking-wide flex items-center gap-2">
                                    <Zap size={14} className="text-[hsl(var(--warning))]" /> Mis Dones y Habilidades
                                </h3>
                                <div className="flex flex-wrap gap-2">
                                    {skills.length === 0 ? (
                                        <p className="text-2xs text-[hsl(var(--text-secondary))] italic">Sin habilidades registradas</p>
                                    ) : skills.map((skill, i) => (
                                        <span key={i} className="px-3 py-1.5 bg-[hsl(var(--surface-2))] rounded-lg text-2xs font-bold text-[hsl(var(--text-secondary))] border border-[hsl(var(--border))] uppercase tracking-wider">
                                            {skill}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] p-4 rounded-lg space-y-3">
                        <h3 className="text-xl font-bold text-[hsl(var(--text-primary))] tracking-tight uppercase italic">Mis <span className="text-[hsl(var(--warning))]">Logros</span></h3>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            {badges.length === 0 ? (
                                <p className="col-span-full text-2xs text-[hsl(var(--text-secondary))] italic">Aún no has obtenido insignias</p>
                            ) : badges.map((badge) => {
                                const Icon = badgeIcon(badge.icon_key);
                                return (
                                    <div key={badge.id} className="bg-[hsl(var(--surface-2))] p-3 rounded-lg flex flex-col items-center gap-3 text-center group hover:bg-[hsl(var(--surface-3))] transition-all border border-[hsl(var(--border))]">
                                        <div className="w-12 h-8 bg-[hsl(var(--surface-1))] rounded-lg flex items-center justify-center text-[hsl(var(--warning))] group-hover:scale-110 transition-transform">
                                            <Icon size={24} />
                                        </div>
                                        <span className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{badge.name}</span>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </div>

                <div className="space-y-3">
                    <div className="bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] p-4 rounded-lg space-y-3">
                        <div className="flex items-center justify-between">
                            <h3 className="text-xl font-bold text-[hsl(var(--text-primary))] tracking-tighter uppercase italic">Nivel <span className="text-[hsl(var(--warning))]">{levelTitle}</span></h3>
                            <Zap size={24} className="text-[hsl(var(--warning))] animate-pulse" />
                        </div>
                        <div className="space-y-2">
                            <div className="flex justify-between text-2xs font-semibold uppercase tracking-wide">
                                <span className="text-[hsl(var(--text-secondary))]">Experiencia Ministerial</span>
                                <span className="text-[hsl(var(--text-primary))]">{xpCurrent} / {xpMax} XP</span>
                            </div>
                            <div className="h-2 bg-[hsl(var(--surface-3))] rounded-full overflow-hidden">
                                <div className="h-full bg-[hsl(var(--warning))] transition-all duration-1000 shadow-[hsl(var(--warning)/0.4)]" style={{ width: `${Math.round(xpProgress)}%` }} />
                            </div>
                        </div>
                        {xpRemaining > 0 && (
                            <p className="text-2xs text-[hsl(var(--text-secondary))] font-medium leading-relaxed italic">
                                &quot;Te faltan {xpRemaining} XP para alcanzar el nivel de {nextLevelTitle}.&quot;
                            </p>
                        )}
                    </div>

                    <div className="bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] p-4 rounded-lg space-y-3">
                        <h3 className="text-xs font-semibold text-[hsl(var(--text-primary))] uppercase tracking-wide">Llamados de Servicio</h3>
                        <div className="space-y-4">
                            {[
                                { title: 'Equipo de Media', desc: 'Necesitamos editores de video para el domingo.' },
                                { title: 'Alabanza', desc: 'Audiciones para coros el proximo martes.' },
                            ].map((call, i) => (
                                <div key={i} className="group p-4 bg-[hsl(var(--surface-2))] rounded-lg border border-[hsl(var(--border))] hover:border-[hsl(var(--warning))] transition-all cursor-pointer">
                                    <div className="flex items-center justify-between mb-1">
                                        <span className="text-xs font-bold text-[hsl(var(--text-primary))] uppercase">{call.title}</span>
                                        <ChevronRight size={14} className="text-[hsl(var(--text-secondary))] group-hover:text-[hsl(var(--warning))] transition-all" />
                                    </div>
                                    <p className="text-2xs text-[hsl(var(--text-secondary))] leading-relaxed">{call.desc}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
        </WorkspaceLayout>
    );
}
