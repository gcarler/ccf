"use client";

import React, { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import {
    ShieldAlert,
    Clock,
    User,
    Activity,
    LayoutDashboard,
    Globe,
    Lock
} from 'lucide-react';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { useAuth } from '@/context/AuthContext';
import { DSCard } from '@/design/components/DSCard';
import { DSBadge } from '@/design/components/DSBadge';
import { toast } from 'sonner';
import { apiFetch } from '@/lib/http';
import { getWorkspaceAuditEventKey, type WorkspaceAuditEvent } from '@/lib/workspaceAudit';

export default function AuditDetailPage() {
    const params = useParams();
    const rawId = params?.id;
    const id = decodeURIComponent((Array.isArray(rawId) ? rawId[0] : rawId) || '');
    const { token } = useAuth();

    const [log, setLog] = useState<WorkspaceAuditEvent | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!token || !id) {
            setLoading(false);
            return;
        }

        const loadLog = async () => {
            try {
                setLoading(true);
                const data = await apiFetch<{ events?: WorkspaceAuditEvent[] }>('/workspace/flags/audit', {
                    token,
                    query: { limit: 1000 },
                    cache: 'no-store',
                });
                const rows = Array.isArray(data?.events) ? data.events : [];
                const match = rows.find((event) => getWorkspaceAuditEventKey(event) === id) || null;
                setLog(match);
            } catch {
                toast.error('Error al cargar el log de auditoría');
            } finally {
                setLoading(false);
            }
        };

        loadLog();
    }, [id, token]);

    if (loading) {
        return <div className="p-4 text-center animate-pulse font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Consultando bitácora de seguridad...</div>;
    }

    if (!log) {
        return (
            <div className="p-4 text-center font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                No se encontró el evento de auditoría.
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--bg-primary))] overflow-hidden">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: 'Administración', icon: LayoutDashboard, href: '/plataforma/admin' },
                    { label: 'Auditoría', icon: ShieldAlert, href: '/plataforma/admin/audit' },
                    { label: `LOG-${id}`, icon: Activity },
                ]}
            />

            <main className="flex-1 overflow-y-auto p-4 lg:p-4">
 <div className="w-full space-y-3">
                    <header className="space-y-4">
                        <div className="flex items-center gap-3">
                            <DSBadge tone="blue" label="SECURITY_LOG" />
                            <DSBadge tone="blue" label={log.action} />
                        </div>
                        <h1 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tight uppercase leading-none">
                            Detalle de Operación
                        </h1>
                    </header>

                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
                        <div className="lg:col-span-2 space-y-3">
                            <DSCard>
                                <h3 className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3">Descripción del Evento</h3>
                                <p className="text-sm text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] leading-relaxed font-medium">
                                    {JSON.stringify({
                                        action: log.action,
                                        feature_id: log.feature_id,
                                        updated_by: log.updated_by,
                                        changes: log.changes || {},
                                    })}
                                </p>
                            </DSCard>

                            <DSCard>
                                <h3 className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3">Metadatos de la Transacción</h3>
                                <div className="bg-[hsl(var(--bg-muted))] rounded-lg p-3 overflow-x-auto">
                                    <pre className="text-emerald-400 text-xs font-mono">
                                        {JSON.stringify(log, null, 4)}
                                    </pre>
                                </div>
                            </DSCard>
                        </div>

                        <aside className="space-y-3">
                            <DSCard>
                                <div className="space-y-3">
                                    <div className="space-y-2">
                                        <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Actor</p>
                                        <div className="flex items-center gap-2">
                                            <div className="size-8 rounded-lg bg-[hsl(var(--bg-muted))] text-white flex items-center justify-center">
                                                <User size={16} />
                                            </div>
                                            <span className="text-xs font-semibold uppercase">{log.updated_by || 'SYS'}</span>
                                        </div>
                                    </div>

                                    <div className="space-y-2">
                                        <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Marca de Tiempo</p>
                                        <div className="flex items-center gap-2 text-xs font-bold text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">
                                            <Clock size={14} /> {new Date(log.timestamp).toLocaleString()}
                                        </div>
                                    </div>

                                    <div className="space-y-2">
                                        <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Feature</p>
                                        <div className="flex items-center gap-2 text-xs font-bold text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">
                                            <Globe size={14} /> {log.feature_id || 'global'}
                                        </div>
                                    </div>

                                    <div className="h-px bg-[hsl(var(--surface-2))] dark:bg-white/5" />

                                    <div className="flex items-center gap-2 font-semibold text-emerald-600 uppercase tracking-wide">
                                        <Lock size={12} /> Registro Inmutable
                                    </div>
                                </div>
                            </DSCard>
                        </aside>
                    </div>
                </div>
            </main>
        </div>
    );
}
