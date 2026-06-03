'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { QRCodeSVG } from 'qrcode.react';
import { ShieldCheck, User, QrCode, Sparkles, Church, Share2, Download, Loader2, Link2, Users } from 'lucide-react';
import { apiFetch } from '@/lib/http';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import CrmShell from '@/components/crm/CrmShell';
import AdminHero from '@/components/admin/AdminHero';

interface Member {
    id: string;
    nombre_completo?: string;
    first_name?: string;
    last_name?: string;
    church_role: string;
    qr_token: string;
    join_date: string;
}

export default function MyCardPage() {
    const [member, setMember] = useState<Member | null>(null);
    const [loading, setLoading] = useState(true);
    const router = useRouter();
    const { token } = useAuth();

    const fetchMyMemberData = useCallback(async () => {
        if (!token) {
            setLoading(false);
            return;
        }
        try {
            const data = await apiFetch<Member>('/crm/personas/me', { token, cache: 'no-store' });
            setMember(data);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    }, [token]);

    useEffect(() => {
        fetchMyMemberData();
    }, [fetchMyMemberData]);

    if (loading) {
        return (
            <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center space-y-4">
                <Loader2 className="animate-spin text-primary" size={48} />
                <p className="text-slate-500 font-bold uppercase tracking-wide text-[10px]">Generando Credencial...</p>
            </div>
        );
    }

    if (!member) {
        return (
            <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4 text-center space-y-3">
                <div className="p-4 bg-rose-500/10 rounded-full text-rose-500">
                    <ShieldCheck size={48} />
                </div>
                <h1 className="text-lg font-bold text-white">Perfil no Encontrado</h1>
                <p className="text-slate-400 max-w-sm">No hemos podido encontrar tu perfil de miembro vinculado a este usuario. Contacta con administración.</p>
                <button onClick={() => router.back()} className="px-3 py-1.5 bg-white/5 hover:bg-white/10 text-white rounded-lg font-bold uppercase tracking-wide text-[10px] transition-all">
                    Volver
                </button>
            </div>
        );
    }

    const getRoleTheme = (role: string) => {
        switch (role?.toLowerCase()) {
            case 'pastor':
                return {
                    name: 'PASTORAL ELITE',
                    primary: 'from-sky-600 to-indigo-900',
                    border: 'border-sky-500/50',
                    badge: 'bg-sky-500',
                    glow: 'shadow-sky-500/20',
                    accent: 'text-sky-300'
                };
            case 'ministro':
                return {
                    name: 'MINISTERIO UNGIDO',
                    primary: 'from-amber-500 to-orange-900',
                    border: 'border-amber-500/50',
                    badge: 'bg-amber-500',
                    glow: 'shadow-amber-500/20',
                    accent: 'text-amber-200'
                };
            case 'joven':
                return {
                    name: 'GENERACIÓN RADICAL',
                    primary: 'from-cyan-500 to-blue-800',
                    border: 'border-cyan-500/50',
                    badge: 'bg-cyan-500',
                    glow: 'shadow-cyan-500/20',
                    accent: 'text-cyan-200'
                };
            case 'servidor':
                return {
                    name: 'SERVIDOR DE REINO',
                    primary: 'from-emerald-500 to-teal-900',
                    border: 'border-emerald-500/50',
                    badge: 'bg-emerald-500',
                    glow: 'shadow-emerald-500/20',
                    accent: 'text-emerald-200'
                };
            default:
                return {
                    name: 'CCF MIEMBRO ACTIVO',
                    primary: 'from-slate-700 to-slate-900',
                    border: 'border-slate-500/50',
                    badge: 'bg-slate-600',
                    glow: 'shadow-slate-500/20',
                    accent: 'text-slate-400'
                };
        }
    };

    const theme = getRoleTheme(member.church_role);

    return (
        <CrmShell
            breadcrumbs={[{ label: 'CCF', icon: Users }, { label: 'Consolidación', icon: Users }, { label: 'Mi carnet', icon: QrCode }]}
            rightActions={
                <button className="flex items-center gap-2 bg-slate-900 px-4 py-2 rounded-lg text-[11px] font-bold text-white hover:bg-black transition-all">
                    <Share2 size={16} /> Compartir
                </button>
            }
        >
        <AdminHero
            eyebrow="Credencial"
            title="Credencial digital"
            description="Comparte tu código personal para validar asistencia y servir. Añádelo a Google Wallet o compártelo en segundos."
            tags={['QR', 'Wallet', 'Seguridad']}
            watchers={['Equipo Identidad', 'Optimus Brain']}
            primaryAction={{ label: 'Descargar PDF', icon: Download, onClick: () => window.print() }}
            secondaryAction={{ label: 'Ver políticas', icon: Link2, onClick: () => router.push('/privacy') }}
        />
        <div className="flex flex-col items-center justify-center space-y-3 pb-4 relative overflow-hidden">
            <div className={`absolute -top-40 -right-40 w-[600px] h-[600px] bg-gradient-to-br ${theme.primary} opacity-20 blur-[120px] rounded-full pointer-events-none`}></div>
            <div className={`absolute -bottom-40 -left-40 w-[600px] h-[600px] bg-gradient-to-tr ${theme.primary} opacity-10 blur-[120px] rounded-full pointer-events-none`}></div>

            <div className={`relative z-10 w-full max-w-[340px] aspect-[4/6] bg-gradient-to-br ${theme.primary} ${theme.border} border rounded-lg shadow-2xl ${theme.glow} overflow-hidden p-4 flex flex-col animate-in zoom-in-95 duration-700 group`}>

                {/* Textures/Overlays */}
                <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/carbon-fibre.png')] opacity-10 mix-blend-overlay"></div>
                <div className="absolute -top-24 -right-24 size-10 bg-white/10 rounded-full blur-3xl"></div>

                {/* Card Header */}
                <div className="flex justify-between items-start relative z-10 mb-3">
                    <Church className="text-white/80" size={32} />
                    <div className={`${theme.badge} px-3 py-1 rounded-full text-[8px] font-bold text-white uppercase tracking-wide`}>
                        {theme.name}
                    </div>
                </div>

                {/* Profile Picture Placeholder */}
                <div className="flex flex-col items-center text-center space-y-4 mb-3 mt-2 relative z-10">
                    <div className="size-10 rounded-lg bg-white/10 backdrop-blur-xl border border-white/20 flex items-center justify-center text-white relative group-hover:scale-105 transition-transform duration-500">
                        <User size={48} className="text-white/50" />
                        <div className="absolute -bottom-1 -right-1 size-6 bg-emerald-500 rounded-lg flex items-center justify-center border-4 border-slate-900 translate-x-1 translate-y-1">
                            <ShieldCheck size={12} className="text-white" />
                        </div>
                    </div>
                    <div>
                        <h1 className="text-lg font-bold text-white tracking-tight leading-tight">
                            {member.nombre_completo || `${member.first_name ?? ''} ${member.last_name ?? ''}`.trim()}
                        </h1>
                        <p className={`text-[10px] font-bold uppercase tracking-wide mt-2 ${theme.accent}`}>
                            {member.church_role} • ID: CCF-{member.id.toString().padStart(4, '0')}
                        </p>
                    </div>
                </div>

                {/* QR Code Container */}
                <div className="flex-1 flex flex-col items-center justify-center relative z-10">
                    <div className="p-4 bg-[hsl(var(--surface-1))] rounded-md shadow-2xl relative group-hover:rotate-1 transition-transform duration-500">
                        <QRCodeSVG
                            value={member.qr_token}
                            size={140}
                            level="H"
                            includeMargin={false}
                            imageSettings={{
                                src: "/ccf-logo-small.png", // Mock logo
                                x: undefined,
                                y: undefined,
                                height: 24,
                                width: 24,
                                excavate: true,
                            }}
                        />
                    </div>
                    <p className="text-[8px] font-bold text-white/40 uppercase tracking-wide mt-3">
                        Escanea para validar asistencia
                    </p>
                </div>

                {/* Bottom Bar */}
                <div className="mt-3 pt-6 border-t border-white/10 relative z-10 flex justify-between items-end">
                    <div className="space-y-1">
                        <p className="text-[7px] font-bold text-white/50 uppercase tracking-wide">Miembro Desde</p>
                        <p className="text-[10px] font-bold text-white">{new Date(member.join_date).toLocaleDateString()}</p>
                    </div>
                    <div className="text-right">
                        <p className="text-[7px] font-bold text-white/50 uppercase tracking-wide">Vigencia</p>
                        <p className="text-[10px] font-bold text-white">2026-2027</p>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-2 gap-4 w-full max-w-sm relative z-10">
                <button className="flex items-center justify-center gap-2 bg-white/5 hover:bg-white/10 border border-white/10 text-white p-4 rounded-md transition-all active:scale-95 group">
                    <Share2 size={18} className="text-slate-400 group-hover:text-primary transition-colors" />
                    <span className="text-[10px] font-bold uppercase tracking-wide">Compartir</span>
                </button>
                <button className="flex items-center justify-center gap-2 bg-white/5 hover:bg-white/10 border border-white/10 text-white p-4 rounded-md transition-all active:scale-95 group">
                    <Download size={18} className="text-slate-400 group-hover:text-emerald-500 transition-colors" />
                    <span className="text-[10px] font-bold uppercase tracking-wide">Descargar</span>
                </button>
                <button className="col-span-2 flex items-center justify-center gap-3 bg-[hsl(var(--surface-1))] text-slate-900 p-3 rounded-md font-bold uppercase tracking-wide text-[11px] shadow-2xl hover:scale-105 transition-all active:scale-95">
                    <Sparkles size={20} className="text-amber-500" /> Añadir a Google Wallet
                </button>
            </div>

            <div className="w-full max-w-[340px] text-center px-3 relative z-10">
                <p className="text-[9px] text-slate-600 font-bold uppercase tracking-wide leading-relaxed">
                    Esta credencial es personal e intransferible. El uso indebido será reportado a la administración del ministerio.
                </p>
            </div>
        </div>
        </CrmShell>
    );
}

