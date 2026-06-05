"use client";

import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import ConfirmActionDrawer, { type ConfirmActionState } from '@/components/ConfirmActionDrawer';
import { motion } from 'framer-motion';
import { AlertCircle,Clock,Globe,LogOut,MapPin,Monitor,RefreshCw,Smartphone,Trash2 } from 'lucide-react';
import React,{ useCallback,useEffect,useState } from 'react';
import { toast } from 'sonner';

interface Session {
    id: number;
    ip_address: string | null;
    user_agent: string | null;
    last_active: string | null;
    created_at: string | null;
    expires_at: string | null;
    is_current: boolean;
}

export default function AdminSettingsSessionsPage() {
    const { token } = useAuth();
    const [sessions, setSessions] = useState<Session[]>([]);
    const [loading, setLoading] = useState(true);
    const [revoking, setRevokeing] = useState<number | null>(null);
    const [confirmAction, setConfirmAction] = useState<ConfirmActionState>(null);

    const fetchSessions = useCallback(async () => {
        try {
            const data = await apiFetch<Session[]>('/auth/sessions', { token });
            // Mark the most recently active session as current
            if (data.length > 0) {
                const sorted = [...data].sort((a, b) => {
                    const ta = new Date(a.last_active || a.created_at || 0).getTime();
                    const tb = new Date(b.last_active || b.created_at || 0).getTime();
                    return tb - ta;
                });
                sorted[0].is_current = true;
                setSessions(sorted);
            } else {
                setSessions([]);
            }
        } catch {
            toast.error('No se pudieron cargar las sesiones');
        } finally {
            setLoading(false);
        }
    }, [token]);

    useEffect(() => { fetchSessions(); }, [fetchSessions]);

    const handleRevoke = async (sessionId: number) => {
        setRevokeing(sessionId);
        try {
            await apiFetch(`/auth/sessions/${sessionId}/revoke`, { method: 'POST', token });
            toast.success('Sesión revocada');
            fetchSessions();
        } catch {
            toast.error('No se pudo revocar la sesión');
        } finally {
            setRevokeing(null);
        }
    };

    const handleRevokeAll = async () => {
        setConfirmAction({
            title: 'Revocar otras sesiones',
            description: 'Se cerrarán todos los demás dispositivos conectados con esta cuenta.',
            destructive: true,
            confirmLabel: 'Revocar sesiones',
            onConfirm: async () => {
                try {
                    const nonCurrent = sessions.filter(s => !s.is_current);
                    for (const s of nonCurrent) {
                        await apiFetch(`/auth/sessions/${s.id}/revoke`, { method: 'POST', token });
                    }
                    toast.success('Todas las demás sesiones fueron revocadas');
                    fetchSessions();
                } catch {
                    toast.error('Error al revocar sesiones');
                }
            },
        });
    };

    const parseDevice = (userAgent: string | null): { icon: React.ElementType; label: string } => {
        if (!userAgent) return { icon: Globe, label: 'Desconocido' };
        const ua = userAgent.toLowerCase();
        if (/mobile|android|iphone|ipad/i.test(ua)) return { icon: Smartphone, label: 'Móvil' };
        if (/chrome|firefox|safari|edge/i.test(ua)) return { icon: Monitor, label: 'Escritorio' };
        return { icon: Globe, label: 'Otro' };
    };

    const parseBrowser = (userAgent: string | null): string => {
        if (!userAgent) return 'Navegador desconocido';
        const ua = userAgent.toLowerCase();
        if (ua.includes('firefox')) return 'Firefox';
        if (ua.includes('edg/')) return 'Edge';
        if (ua.includes('chrome') && !ua.includes('chromium')) return 'Chrome';
        if (ua.includes('safari')) return 'Safari';
        return 'Navegador';
    };

    const parseOS = (userAgent: string | null): string => {
        if (!userAgent) return 'Sistema desconocido';
        const ua = userAgent.toLowerCase();
        if (ua.includes('windows')) return 'Windows';
        if (ua.includes('macintosh') || ua.includes('mac os')) return 'macOS';
        if (ua.includes('linux')) return 'Linux';
        if (ua.includes('android')) return 'Android';
        if (ua.includes('iphone') || ua.includes('ipad')) return 'iOS';
        return 'Sistema';
    };

    const timeAgo = (dateStr: string | null): string => {
        if (!dateStr) return 'Desconocido';
        const now = new Date();
        const date = new Date(dateStr);
        const diffMs = now.getTime() - date.getTime();
        const diffMin = Math.floor(diffMs / 60000);
        if (diffMin < 1) return 'Ahora';
        if (diffMin < 60) return `Hace ${diffMin} min`;
        const diffHr = Math.floor(diffMin / 60);
        if (diffHr < 24) return `Hace ${diffHr}h`;
        const diffDay = Math.floor(diffHr / 24);
        return `Hace ${diffDay}d`;
    };

    return (
        <div className="min-h-full bg-slate-950/20 font-display">
            {/* Header */}
            <div className="bg-slate-900/40 backdrop-blur-xl border-b border-white/5 sticky top-0 z-20">
                <div className="px-4 py-2 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-blue-500/10 text-[hsl(var(--primary))]">
                            <Monitor size={18} />
                        </div>
                        <div>
                            <h1 className="text-sm font-bold text-white">Sesiones Activas</h1>
                            <p className="text-[11px] text-slate-400">Dispositivos conectados a tu cuenta</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={fetchSessions}
                            className="p-2 rounded-lg bg-white/5 border border-white/10 text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
                            title="Actualizar"
                        >
                            <RefreshCw size={14} />
                        </button>
                        {sessions.length > 1 && (
                            <button
                                onClick={handleRevokeAll}
                                className="px-3 py-1.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-[11px] font-semibold hover:bg-rose-500/20 transition-colors flex items-center gap-1.5"
                            >
                                <LogOut size={13} />
                                Revocar todas
                            </button>
                        )}
                    </div>
                </div>
            </div>

            {/* Content */}
            <div className="p-4 max-w-3xl mx-auto space-y-3">
                {loading ? (
                    <div className="flex items-center justify-center py-12">
                        <RefreshCw size={24} className="animate-spin text-slate-500" />
                    </div>
                ) : sessions.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-12 text-center bg-white/5 border border-white/10 rounded-lg">
                        <AlertCircle size={32} className="text-slate-500 mb-2" />
                        <p className="text-sm font-medium text-slate-400">Sin sesiones activas</p>
                        <p className="text-xs text-slate-500">Inicia sesión para ver tus dispositivos</p>
                    </div>
                ) : (
                    sessions.map((session, i) => {
                        const device = parseDevice(session.user_agent);
                        const browser = parseBrowser(session.user_agent);
                        const os = parseOS(session.user_agent);
                        const DeviceIcon = device.icon;

                        return (
                            <motion.div
                                key={session.id}
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: i * 0.05 }}
                                className={`bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] border rounded-lg p-4 transition-all ${
                                    session.is_current
                                        ? 'border-blue-500/30 shadow-lg shadow-blue-500/5'
                                        : 'border-white/10 hover:border-white/20'
                                }`}
                            >
                                <div className="flex items-start justify-between">
                                    <div className="flex items-start gap-3 flex-1">
                                        <div className={`p-2 rounded-lg ${
                                            session.is_current
                                                ? 'bg-blue-500/10 text-[hsl(var(--primary))]'
                                                : 'bg-slate-100 dark:bg-white/5 text-slate-400'
                                        }`}>
                                            <DeviceIcon size={18} />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2">
                                                <span className="text-sm font-semibold text-slate-800 dark:text-white">
                                                    {browser}
                                                </span>
                                                {session.is_current && (
                                                    <span className="px-2 py-0.5 rounded-full bg-blue-500/10 text-[hsl(var(--primary))] text-[10px] font-bold uppercase">
                                                        Actual
                                                    </span>
                                                )}
                                            </div>
                                            <p className="text-xs text-slate-400 mt-0.5">
                                                {os} · {device.label}
                                            </p>
                                            <div className="flex items-center gap-4 mt-2 text-[11px] text-slate-500">
                                                {session.ip_address && (
                                                    <span className="flex items-center gap-1">
                                                        <MapPin size={11} />
                                                        {session.ip_address}
                                                    </span>
                                                )}
                                                <span className="flex items-center gap-1">
                                                    <Clock size={11} />
                                                    {timeAgo(session.last_active)}
                                                </span>
                                            </div>
                                        </div>
                                    </div>

                                    {!session.is_current && (
                                        <button
                                            onClick={() => handleRevoke(session.id)}
                                            disabled={revoking === session.id}
                                            className="p-2 rounded-lg text-slate-400 hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-900/20 transition-colors disabled:opacity-50"
                                            title="Revocar sesión"
                                        >
                                            {revoking === session.id ? (
                                                <RefreshCw size={14} className="animate-spin" />
                                            ) : (
                                                <Trash2 size={14} />
                                            )}
                                        </button>
                                    )}
                                </div>
                            </motion.div>
                        );
                    })
                )}
            </div>

            <ConfirmActionDrawer action={confirmAction} onClose={() => setConfirmAction(null)} />
        </div>
    );
}
